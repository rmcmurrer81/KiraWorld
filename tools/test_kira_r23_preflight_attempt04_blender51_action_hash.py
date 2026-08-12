#!/usr/bin/env python3
"""Focused tests for R23 Attempt 04's Blender 5.1 action serializer."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from tools.kira_r23_blender51_action_serializer import (
    action_inventory,
    actions_sha256,
    serialize_actions,
)


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "Tools/blender_preflight_kira_r23_cc0_afes_expanded_mask_attempt04.py"
SERIALIZER = ROOT / "Tools/kira_r23_blender51_action_serializer.py"
ADDENDUM = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_attempt04_preparation/"
    "KIRA_R23_ATTEMPT04_BLENDER51_ACTION_HASH_ADDENDUM.json"
)
PASS_EVIDENCE = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask/preflight_attempt_04/PREFLIGHT.json"
)
FAILURE_EVIDENCE = PASS_EVIDENCE.with_name("FAILURE_EVIDENCE.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(x, y):
    return NS(
        co=NS(x=x, y=y),
        handle_left=NS(x=x - 0.1, y=y - 0.2),
        handle_right=NS(x=x + 0.1, y=y + 0.2),
        handle_left_type="AUTO",
        handle_right_type="VECTOR",
        interpolation="BEZIER",
        easing="AUTO",
    )


def curve(path, index, value):
    return NS(
        data_path=path,
        array_index=index,
        extrapolation="CONSTANT",
        keyframe_points=[point(1.0, value), point(2.0, value + 1.0)],
    )


class LayeredAction:
    def __init__(self):
        self.name = "LayeredAction"
        self.frame_range = (1.0, 20.0)
        self.use_fake_user = True
        self.slots = [
            NS(handle=9, identifier="OBNine", target_id_type="OBJECT"),
            NS(handle=2, identifier="OBTwo", target_id_type="OBJECT"),
        ]
        self.layers = [
            NS(
                name="Base Layer",
                strips=[
                    NS(
                        type="KEYFRAME",
                        channelbags=[
                            NS(slot_handle=9, fcurves=[curve("location", 2, 4.0)]),
                            NS(slot_handle=2, fcurves=[curve("rotation_euler", 1, 8.0)]),
                        ],
                    )
                ],
            )
        ]


def legacy_action():
    return NS(
        name="LegacyAction",
        frame_range=(1.0, 10.0),
        use_fake_user=False,
        fcurves=[curve("location", 1, 2.0), curve("location", 0, 3.0)],
    )


class Attempt04ActionHashTests(unittest.TestCase):
    def setUp(self):
        self.addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))

    def test_serializer_and_wrapper_parse(self):
        ast.parse(SERIALIZER.read_text(encoding="utf-8"))
        ast.parse(WRAPPER.read_text(encoding="utf-8"))

    def test_legacy_fcurves_and_complete_keyframe_handles_are_retained(self):
        rows = serialize_actions([legacy_action()])
        self.assertEqual(rows[0]["storage"], "legacy")
        self.assertEqual(len(rows[0]["fcurves"]), 2)
        self.assertEqual(rows[0]["fcurves"][0]["array_index"], 0)
        key = rows[0]["fcurves"][0]["keyframes"][0]
        self.assertIn("handle_left", key)
        self.assertIn("handle_right", key)
        self.assertIn("handle_left_type", key)
        self.assertIn("handle_right_type", key)
        self.assertIn("interpolation", key)
        self.assertIn("easing", key)

    def test_layered_slots_channelbag_handles_and_curves_are_retained(self):
        rows = serialize_actions([LayeredAction()])
        row = rows[0]
        self.assertEqual(row["storage"], "layered")
        self.assertEqual([slot["handle"] for slot in row["slots"]], [2, 9])
        bags = row["layers"][0]["strips"][0]["channelbags"]
        self.assertEqual([bag["slot_handle"] for bag in bags], [2, 9])
        self.assertEqual(len(bags[0]["fcurves"]), 1)
        self.assertEqual(len(bags[0]["fcurves"][0]["keyframes"]), 2)

    def test_hash_is_deterministic_and_sensitive_to_slot_and_key_data(self):
        legacy = legacy_action()
        layered = LayeredAction()
        digest = actions_sha256([layered, legacy])
        self.assertEqual(digest, actions_sha256([legacy, layered]))
        changed = LayeredAction()
        changed.slots[0].handle = 10
        self.assertNotEqual(digest, actions_sha256([legacy_action(), changed]))
        changed_key = LayeredAction()
        changed_key.layers[0].strips[0].channelbags[0].fcurves[0].keyframe_points[0].co.y += 0.5
        self.assertNotEqual(digest, actions_sha256([legacy_action(), changed_key]))

    def test_inventory_proves_no_actions_omitted(self):
        rows = serialize_actions([legacy_action(), LayeredAction()])
        inventory = action_inventory(rows)
        self.assertEqual(inventory["action_count"], 2)
        self.assertEqual(inventory["action_names"], ["LayeredAction", "LegacyAction"])
        self.assertEqual(inventory["storage_counts"], {"legacy": 1, "layered": 1})
        self.assertEqual(inventory["slot_count"], 2)
        self.assertEqual(inventory["channelbag_count"], 2)
        self.assertEqual(inventory["fcurve_count"], 4)
        self.assertEqual(inventory["keyframe_count"], 8)
        self.assertFalse(inventory["actions_omitted"])

    def test_overlay_preserves_attempts_and_all_exact_bindings(self):
        rows = [
            self.addendum["base_worker"],
            self.addendum["base_config"],
            self.addendum["attempt03_contract_addendum"],
            self.addendum["source_blend"],
            self.addendum["qualified_cc0_foundation"],
            *self.addendum["proven_serializer_sources"],
            *self.addendum["preserved_attempts"],
        ]
        for row in rows:
            path = ROOT / row["path"]
            self.assertTrue(path.is_file(), row["path"])
            self.assertEqual(path.stat().st_size, row["bytes"], row["path"])
            self.assertEqual(sha256(path), row["sha256"], row["path"])
        self.assertEqual(
            [row["attempt_id"] for row in self.addendum["preserved_attempts"]],
            ["attempt_01", "attempt_02", "attempt_03"],
        )

    def test_contract_changes_only_action_hasher_and_retains_040(self):
        contract = self.addendum["contract"]
        self.assertEqual(contract["world_extent_addendum_retained_m"], 0.4)
        self.assertEqual(contract["only_runtime_function_replaced"], "actions_sha256")
        self.assertFalse(contract["omit_actions_allowed"])
        self.assertFalse(contract["mask_or_chart_changed"])
        self.assertFalse(
            contract["gate_or_threshold_changed_beyond_preserved_attempt03_addendum"]
        )
        tree = ast.parse(WRAPPER.read_text(encoding="utf-8"))
        base_targets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                base_targets.extend(
                    ast.unparse(target)
                    for target in node.targets
                    if ast.unparse(target).startswith("base.")
                )
        self.assertEqual(set(base_targets), {"base.actions_sha256"})

    def test_wrapper_has_no_authoring_save_render_or_export_call(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("bpy.ops", source)
        for token in (
            "save_as_mainfile(",
            "save_mainfile(",
            "render.render(",
            "export_scene.",
            "wm.open_mainfile(",
        ):
            self.assertNotIn(token, source)

    def test_actual_attempt04_evidence_if_present(self):
        if not PASS_EVIDENCE.exists() and not FAILURE_EVIDENCE.exists():
            self.skipTest("Attempt 04 has not been run yet")
        self.assertNotEqual(PASS_EVIDENCE.exists(), FAILURE_EVIDENCE.exists())
        path = PASS_EVIDENCE if PASS_EVIDENCE.exists() else FAILURE_EVIDENCE
        evidence = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["attempt_id"], "attempt_04")
        if PASS_EVIDENCE.exists():
            action = evidence["blender51_action_freeze_ledger"]
            self.assertFalse(action["actions_omitted"])
            self.assertTrue(action["freeze_ledger_actions_sha256_matches"])
            self.assertTrue(all(evidence["deterministic_selection_checks"].values()))
            self.assertTrue(evidence["explicit_locality_escape_proof"]["passed"])
            self.assertIn("fresh_freeze_ledger", evidence)
            self.assertTrue(evidence["integrity"]["source_blend_exact"])
            self.assertTrue(evidence["integrity"]["r19_body_exact"])
        else:
            self.assertEqual(evidence["status"], "PREFLIGHT_NO_GO_NO_CANDIDATE")
            self.assertEqual(
                evidence["source_blend"]["sha256_after"],
                evidence["source_blend"]["expected_sha256"],
            )


if __name__ == "__main__":
    unittest.main()

