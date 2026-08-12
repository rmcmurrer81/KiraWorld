#!/usr/bin/env python3
"""Non-Blender tests for the prepared Kira R21 movement Attempt-04 contract."""

from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "Tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import kira_r21_movement_attempt04_contract as contract  # noqa: E402


CONFIG_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r21_action_only_movement_correction/"
    "MOVEMENT_CONFIG_ATTEMPT_04_PREPARED.json"
)
WORKER_PATH = TOOLS_DIR / "blender_author_kira_r21_action_only_movement_attempt04.py"


class Attempt04ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = contract.load_json(CONFIG_PATH)
        cls.sequences = {value["id"]: value for value in cls.config["sequences"]}

    def test_prepared_contract_is_complete_and_not_released(self) -> None:
        summary = contract.validate_config(self.config)
        self.assertEqual(summary["sequence_count"], 12)
        self.assertEqual(summary["phase_count"], 68)
        self.assertEqual(summary["evidence_view_count"], 62)
        self.assertEqual(summary["required_evidence_count"], 17)
        self.assertTrue(summary["prepared_only"])
        self.assertFalse(summary["blender_execution_authorized"])
        self.assertIsNone(self.config["execution_release"])

    def test_current_and_attempt03_anchors_are_exact(self) -> None:
        actual = contract.validate_local_anchors(self.config, PROJECT_ROOT)
        self.assertEqual(len(actual), 5)
        self.assertEqual(
            actual[self.config["preserved_attempt_03"]["blend"]],
            "4ecff35f92ceee614f17b9ad391ac36b9cf6fcdfb4d79449063a0cd67a03b8f3",
        )

    def test_release_cannot_be_inferred_or_partially_supplied(self) -> None:
        prepared_hash = contract.sha256_file(CONFIG_PATH)
        with self.assertRaises(contract.ContractError):
            contract.validate_release(
                self.config,
                {"schema_version": 1, "authorized_for_blender_execution": False},
                prepared_hash,
                PROJECT_ROOT,
            )
        with self.assertRaises(contract.ContractError):
            contract.validate_release(
                self.config,
                {
                    "schema_version": 1,
                    "authorized_for_blender_execution": True,
                    "prepared_config_sha256": prepared_hash,
                    "pelvic_and_nail_priorities_complete": False,
                },
                prepared_hash,
                PROJECT_ROOT,
            )

    def test_source_binding_is_deferred_behind_pelvic_and_nail_work(self) -> None:
        binding = self.config["source_binding"]
        self.assertEqual(
            binding["mode"],
            "DEFERRED_UNTIL_PELVIC_AND_NAIL_PRIORITIES_COMPLETE",
        )
        for key in (
            "execution_source_blend",
            "execution_source_sha256",
            "execution_source_evidence",
            "execution_source_evidence_sha256",
        ):
            self.assertIsNone(binding[key])

    def test_only_append_only_action_mutation_is_permitted(self) -> None:
        protected = self.config["protected_component_contract"]
        self.assertTrue(protected["only_append_only_actions_allowed"])
        for key in (
            "body_mesh_mutation_allowed",
            "rest_rig_mutation_allowed",
            "weight_mutation_allowed",
            "material_mutation_allowed",
        ):
            self.assertFalse(protected[key])
        self.assertTrue(self.config["preserved_attempt_03"]["must_remain_byte_exact"])
        self.assertTrue(self.config["preserved_attempt_03"]["must_not_be_used_as_source"])

    def test_natural_neutral_arms_are_not_presentation_wide(self) -> None:
        phase = self.sequences["natural_neutral_arms"]["phases"][0]
        pose = contract.generate_phase_pose(self.config, phase)["rotations_degrees_xyz"]
        bones = self.config["bone_map"]
        left = pose[bones["left"]["shoulder"]]
        right = pose[bones["right"]["shoulder"]]
        self.assertLessEqual(abs(left[2]), 8.0)
        self.assertLessEqual(abs(right[2]), 8.0)
        self.assertNotEqual(left, [0.0, 0.0, 0.0])
        self.assertNotEqual(right, [0.0, 0.0, 0.0])

    def test_gaits_have_reciprocal_arm_swing_and_bilateral_contacts(self) -> None:
        bones = self.config["bone_map"]
        for speed in ("walk", "jog", "run"):
            sequence = self.sequences[f"{speed}_cycle"]
            planted = {phase.get("planted_foot") for phase in sequence["phases"]}
            self.assertIn("left", planted)
            self.assertIn("right", planted)
            first_pose = contract.generate_phase_pose(self.config, sequence["phases"][0])
            last_pose = contract.generate_phase_pose(self.config, sequence["phases"][-1])
            self.assertEqual(first_pose, last_pose)
            for phase in sequence["phases"]:
                pose = contract.generate_phase_pose(self.config, phase)["rotations_degrees_xyz"]
                left_arm = pose[bones["left"]["shoulder"]][0]
                right_arm = pose[bones["right"]["shoulder"]][0]
                left_leg = pose[bones["left"]["thigh"]][0]
                right_leg = pose[bones["right"]["thigh"]][0]
                self.assertLessEqual(left_arm * left_leg, 0.0)
                self.assertLessEqual(right_arm * right_leg, 0.0)

    def test_object_sequences_have_reach_grasp_retract_hold(self) -> None:
        for name in ("book", "tablet", "phone"):
            sequence = self.sequences[f"{name}_reach_grasp_retract_hold"]
            ids = [phase["id"] for phase in sequence["phases"]]
            self.assertEqual(ids, ["neutral", "reach", "grasp", "retract", "hold"])
            grasp = next(phase for phase in sequence["phases"] if phase["id"] == "grasp")
            self.assertEqual(grasp["prop_mode"], "fixed")
            self.assertTrue(any(contact.get("grip") for contact in grasp["contacts"]))
            for phase_id in ("retract", "hold"):
                phase = next(value for value in sequence["phases"] if value["id"] == phase_id)
                self.assertTrue(phase["prop_mode"].startswith("follow_"))

    def test_grip_closes_thumb_and_all_four_fingers(self) -> None:
        sequence = self.sequences["phone_reach_grasp_retract_hold"]
        phase = next(value for value in sequence["phases"] if value["id"] == "grasp")
        pose = contract.generate_phase_pose(self.config, phase)["rotations_degrees_xyz"]
        right = self.config["bone_map"]["right"]
        for digit in ("thumb", "index", "middle", "ring", "pinky"):
            for bone in right[digit]:
                self.assertIn(bone, pose)
                self.assertGreater(abs(pose[bone][0]), 0.0)

    def test_door_washing_shower_and_bath_phase_inventories(self) -> None:
        for sequence_id, expected in contract.REQUIRED_PHASES.items():
            actual = tuple(value["id"] for value in self.sequences[sequence_id]["phases"])
            self.assertEqual(actual, expected)

    def test_every_declared_grip_has_close_hand_arm_prop_evidence(self) -> None:
        for sequence in self.config["sequences"]:
            views: dict[str, set[str]] = {}
            for request in sequence.get("evidence_views", []):
                views.setdefault(request["phase"], set()).add(request["view"])
            for phase in sequence["phases"]:
                if any(bool(contact.get("grip")) for contact in phase.get("contacts", [])):
                    self.assertTrue(
                        any(
                            "prop_close" in view or "handle_wrist_close" in view
                            for view in views.get(phase["id"], set())
                        ),
                        f"{sequence['id']}:{phase['id']}",
                    )

    def test_expected_action_and_render_names_are_unique(self) -> None:
        actions = contract.expected_action_names(self.config)
        renders = contract.expected_render_labels(self.config)
        self.assertEqual(len(actions), 12)
        self.assertEqual(len(actions), len(set(actions)))
        self.assertEqual(len(renders), 62)
        self.assertEqual(len(renders), len(set(renders)))
        self.assertTrue(all(value.startswith("KIRA_R21_MOVEMENT_ATTEMPT04_") for value in actions))

    def test_worker_is_syntax_valid_and_release_guard_precedes_mutation(self) -> None:
        source = WORKER_PATH.read_text(encoding="utf-8")
        ast.parse(source)
        release_guard = source.index('if not release_path.is_file():')
        output_creation = source.index('recovery_dir.mkdir(parents=True, exist_ok=False)')
        blender_save = source.index('bpy.ops.wm.save_as_mainfile')
        self.assertLess(release_guard, output_creation)
        self.assertLess(output_creation, blender_save)
        self.assertNotIn('save_as_mainfile(filepath=str(attempt03_path)', source)

    def test_output_directories_do_not_exist_during_preparation(self) -> None:
        outputs = self.config["future_outputs"]
        self.assertFalse((PROJECT_ROOT / outputs["recovery_output_dir"]).exists())
        self.assertFalse((PROJECT_ROOT / outputs["owner_review_output_dir"]).exists())

    def test_contract_rejects_missing_sequence_and_weakened_intersection_gate(self) -> None:
        missing = deepcopy(self.config)
        missing["sequences"] = missing["sequences"][:-1]
        with self.assertRaises(contract.ContractError):
            contract.validate_config(missing)
        weakened = deepcopy(self.config)
        weakened["acceptance_gates"]["maximum_pose_induced_or_exposed_self_intersection_pairs"] = 1
        with self.assertRaises(contract.ContractError):
            contract.validate_config(weakened)


if __name__ == "__main__":
    unittest.main(verbosity=2)
