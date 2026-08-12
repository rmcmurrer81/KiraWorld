#!/usr/bin/env python3
"""Focused tests for R23 read-only preflight Attempt 02 retention."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest

from tools.kira_r23_attempt02_failure_retention import (
    retain_preflight_failure_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "Tools/blender_preflight_kira_r23_cc0_afes_expanded_mask_attempt02.py"
HELPER = ROOT / "Tools/kira_r23_attempt02_failure_retention.py"
OVERLAY = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_attempt02_preparation/"
    "KIRA_R23_ATTEMPT02_FAILURE_RETENTION_OVERLAY.json"
)
ATTEMPT02_EVIDENCE = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask/preflight_attempt_02/"
    "FAILURE_EVIDENCE.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_locals():
    attempts = [
        {
            "exterior_rings": rings,
            "topology": {
                "face_count": 1000 + rings,
                "component_count": 1,
                "boundary_cycle_count": 1,
                "euler_characteristic": 1,
                "is_one_disk": True,
            },
            "bounds_world_m": {
                "minimum": [-0.1, -0.2, 0.8],
                "maximum": [0.1, 0.2, 1.0],
            },
            "world_extent_m": 0.4 + rings / 100.0,
            "lateral_half_extent_m": 0.1,
            "dominant_rig_groups": ["pelvis_04"],
            "unexpected_dominant_rig_groups": [],
            "gates": {
                "one_disk": True,
                "face_count_bounded": True,
                "world_extent_bounded": False,
                "lateral_half_extent_bounded": True,
                "outer_seam_count_bounded": True,
                "old_patch_fully_contained": True,
                "projected_hits_fully_contained": True,
                "dominant_rig_groups_local": True,
            },
        }
        for rings in (2, 3, 4)
    ]
    preflight = {
        "inputs": {"source": {"sha256": "a" * 64}},
        "authority": {"qualified": True, "license": "CC0-1.0"},
        "r19_evidence_contract": {"passed": True},
        "old_record": {"face_count": 376},
        "donor_evidence": {"selected_disk_face_rings": 1},
        "projection": {"hit_fraction": 1.0},
        "source_hash_before": "b" * 64,
        "body_state_before": "c" * 64,
        "body_state_after_donor_append": "c" * 64,
    }
    expanded = {
        "mask_config": {"expanded_mask_exterior_ring_candidates": [2, 3, 4]},
        "attempts": attempts,
        "allowed": {1, 2, 3, 4},
        "path_union": {2, 3},
        "target_distances": {7: 2, 8: 5},
        "hit_faces": {3, 4},
        "old_patch": {1, 2},
        "old_hit_fraction": 0.5,
        "minimum_old_fraction": 0.98,
        "group_old_records": {"AFES": {"passed": False}},
        "old_mask_fit": False,
    }
    return preflight, expanded, attempts


class Attempt02RetentionTests(unittest.TestCase):
    def test_python_sources_parse(self):
        ast.parse(WRAPPER.read_text(encoding="utf-8"))
        ast.parse(HELPER.read_text(encoding="utf-8"))

    def test_overlay_binds_exact_sealed_inputs_and_attempt01(self):
        overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
        self.assertEqual(overlay["attempt_id"], "attempt_02")
        for name in (
            "base_worker",
            "base_config",
            "source_blend",
            "qualified_cc0_foundation",
            "preserved_attempt_01",
        ):
            binding = overlay[name]
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.stat().st_size, binding["bytes"], name)
            self.assertEqual(sha256(path), binding["sha256"], name)

    def test_overlay_changes_only_failure_retention(self):
        overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
        change = overlay["only_change"]
        self.assertTrue(change["base_preflight_function_executed_unchanged"])
        self.assertTrue(change["base_expanded_mask_function_executed_unchanged"])
        self.assertFalse(change["source_or_mesh_logic_changed"])
        self.assertFalse(change["mapping_logic_changed"])
        self.assertFalse(change["gate_or_threshold_changed"])
        self.assertFalse(change["search_rings_changed"])
        self.assertEqual(overlay["required_complete_ring_attempts"], [2, 3, 4])

    def test_wrapper_calls_base_without_replacing_selector(self):
        source = WRAPPER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        function_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        self.assertNotIn("expanded_mask_record", function_names)
        assignment_targets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                assignment_targets.extend(node.targets)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                assignment_targets.append(node.target)
        self.assertNotIn(
            "base.expanded_mask_record",
            {ast.unparse(target) for target in assignment_targets},
        )
        self.assertIn("return base.preflight(config, config_path)", source)
        self.assertIn("sys.settrace(global_trace)", source)

    def test_wrapper_has_no_authoring_save_render_or_export_call(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("bpy.ops", source)
        for forbidden in (
            "save_as_mainfile(",
            "save_mainfile(",
            "render.render(",
            "export_scene.",
            "wm.open_mainfile(",
        ):
            self.assertNotIn(forbidden, source)

    def test_complete_attempts_array_and_all_nested_metrics_are_retained(self):
        preflight, expanded, attempts = sample_locals()
        result = retain_preflight_failure_metrics(preflight, expanded)
        mask = result["expanded_r19_mask_failure"]
        self.assertEqual(mask["attempts"], attempts)
        self.assertEqual(mask["retention"]["recorded_exterior_rings"], [2, 3, 4])
        self.assertEqual(mask["retention"]["attempt_count"], 3)
        self.assertTrue(mask["retention"]["complete_attempts_array"])
        self.assertEqual(
            mask["attempts"][2]["gates"], attempts[2]["gates"]
        )
        json.dumps(result)

    def test_incomplete_attempts_array_is_truthfully_flagged(self):
        preflight, expanded, _attempts = sample_locals()
        expanded["attempts"] = expanded["attempts"][:2]
        result = retain_preflight_failure_metrics(preflight, expanded)
        retention = result["expanded_r19_mask_failure"]["retention"]
        self.assertEqual(retention["recorded_exterior_rings"], [2, 3])
        self.assertFalse(retention["complete_attempts_array"])

    def test_attempt02_output_is_distinct_and_append_only(self):
        overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
        self.assertEqual(
            overlay["output"]["directory"],
            "RecoverySprint/continuation_20260803/"
            "kira_r23_cc0_afes_expanded_mask/preflight_attempt_02",
        )
        self.assertTrue(overlay["output"]["append_only"])
        self.assertNotEqual(
            overlay["output"]["directory"],
            str(Path(overlay["preserved_attempt_01"]["path"]).parent).replace(
                "\\", "/"
            ),
        )

    def test_actual_failure_evidence_contains_complete_attempts_array(self):
        self.assertTrue(ATTEMPT02_EVIDENCE.is_file())
        evidence = json.loads(ATTEMPT02_EVIDENCE.read_text(encoding="utf-8"))
        self.assertTrue(
            evidence["retention_gate"]["complete_attempts_array_present"]
        )
        attempts = evidence["retained_pre_failure_metrics"][
            "expanded_r19_mask_failure"
        ]["attempts"]
        self.assertEqual(
            [row["exterior_rings"] for row in attempts], [2, 3, 4]
        )
        for row in attempts:
            self.assertIn("topology", row)
            self.assertIn("bounds_world_m", row)
            self.assertIn("world_extent_m", row)
            self.assertIn("lateral_half_extent_m", row)
            self.assertIn("dominant_rig_groups", row)
            self.assertIn("unexpected_dominant_rig_groups", row)
            self.assertIn("gates", row)
            self.assertEqual(
                [name for name, passed in row["gates"].items() if not passed],
                ["world_extent_bounded"],
            )


if __name__ == "__main__":
    unittest.main()
