#!/usr/bin/env python3
"""Ordinary-Python integrity tests for the unbound R23 verifier package."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_postsave_fresh_reopen_verifier_preparation"
)
CONFIG_PATH = PACKAGE / "KIRA_R23_POSTSAVE_VERIFIER_CONFIG_TEMPLATE.json"
WORKER_PATH = ROOT / "Tools/blender_verify_kira_r23_postsave_fresh_reopen.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class R23PostsavePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.source = WORKER_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(WORKER_PATH))

    def test_template_is_deliberately_unbound_and_nonexecutable(self) -> None:
        self.assertEqual(
            self.config["status"], "TEMPLATE_DEFERRED_UNBOUND_NOT_EXECUTABLE"
        )
        self.assertIsNone(self.config["attempt_id"])
        self.assertFalse(self.config["execution"]["enabled"])
        for section in ("candidate_binding", "build_evidence_binding"):
            self.assertEqual(
                self.config[section], {"path": None, "bytes": None, "sha256": None}
            )
        self.assertIsNone(self.config["bound_output"]["evidence_directory"])
        self.assertIsNone(self.config["bound_output"]["owner_render_directory"])

    def test_fixed_inputs_exist_and_match_their_hashes(self) -> None:
        for label, record in self.config["fixed_inputs"].items():
            with self.subTest(label=label):
                self.assertIsNotNone(record.get("sha256"))
                path = ROOT / record["path"]
                self.assertTrue(path.is_file(), path)
                self.assertEqual(sha256_file(path), record["sha256"])
                if record.get("bytes") is not None:
                    self.assertEqual(path.stat().st_size, record["bytes"])

    def test_exact_r19_source_and_freeze_ledgers_are_pinned(self) -> None:
        source = self.config["fixed_inputs"]["r19_source_blend"]
        self.assertEqual(source["bytes"], 90861425)
        self.assertEqual(
            source["sha256"],
            "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f",
        )
        frozen = self.config["frozen_r19_ledgers"]
        self.assertEqual(
            set(frozen),
            {
                "surviving_primary_surface_canonical_state_sha256",
                "outer_seam_canonical_state_sha256",
                "nonbody_mesh_ledger_sha256",
                "existing_body_material_ledger_sha256",
                "rig_rest_structure_sha256",
                "actions_sha256",
            },
        )
        self.assertTrue(all(len(value) == 64 for value in frozen.values()))

    def test_all_required_machine_gate_domains_are_explicit(self) -> None:
        gates = set(self.config["machine_gates"])
        required = {
            "exact_candidate_build_evidence_binding",
            "exact_r19_source_hash_and_size_preserved_before_and_after",
            "fresh_factory_startup_source_then_candidate_reopen",
            "whole_body_single_component_closed_manifold_topology",
            "exact_neutral_self_intersections_compared_with_inherited_r19_baseline",
            "zero_patch_involving_exact_intersection_pairs",
            "seam_position_continuity",
            "seam_normal_continuity",
            "seam_tangent_continuity",
            "seam_uv_continuity",
            "seam_and_patch_native_weight_continuity",
            "existing_material_graphs_exact_and_one_new_bounded_tint",
            "nonbody_mesh_hashes_exact",
            "rig_rest_hash_exact",
            "action_hash_exact",
            "neutral_and_required_pose_deformation_metrics",
            "arm_hand_and_finger_reach_deformation_metrics",
            "seated_toilet_seated_and_supine_support_contact_metrics",
            "all_required_private_owner_render_files_readable",
            "no_source_candidate_save_export_activation_assignment_or_publication",
        }
        self.assertTrue(required.issubset(gates), required - gates)

    def test_required_pose_set_is_complete(self) -> None:
        poses = {item["id"] for item in self.config["poses"]}
        self.assertEqual(
            poses,
            {
                "neutral",
                "left_knee_bend",
                "right_knee_bend",
                "bilateral_knee_bend",
                "hip_flexion",
                "hip_abduction",
                "seated_contact",
                "toilet_seated",
                "supine",
                "eating_reach",
                "hand_presentation",
            },
        )
        supports = {item["id"]: item["support"] for item in self.config["poses"]}
        self.assertEqual(supports["seated_contact"], "seat")
        self.assertEqual(supports["toilet_seated"], "toilet_seat_proxy")
        self.assertEqual(supports["supine"], "bed_plane")

    def test_owner_render_plan_covers_every_required_view_and_deformation(self) -> None:
        renders = self.config["owner_render_plan"]
        ids = [item["id"] for item in renders]
        self.assertEqual(len(ids), len(set(ids)))
        required_ids = {
            "neutral_front",
            "neutral_left_oblique",
            "neutral_right_oblique",
            "neutral_left_side",
            "neutral_right_side",
            "neutral_rear",
            "inferior_front",
            "inferior_rear_perineal",
            "neutral_distance",
            "left_knee_bend",
            "right_knee_bend",
            "bilateral_knee_bend_front",
            "bilateral_knee_bend_side",
            "hip_flexion",
            "hip_abduction",
            "seated_contact_front_oblique",
            "seated_contact_side",
            "toilet_seated_front_oblique",
            "toilet_seated_side",
            "supine_top",
            "supine_side",
            "patch_seam_close",
            "perineal_close",
            "pelvic_anterior_clinical_close",
            "pelvic_inferior_clinical_close",
            "perineal_left_clinical",
            "perineal_right_clinical",
            "pelvic_seated_contact_close",
            "pelvic_toilet_seated_close",
            "eating_reach_full",
            "eating_reach_left_hand_close",
            "hand_presentation_front",
            "hand_presentation_hands_close",
        }
        self.assertEqual(set(ids), required_ids)
        pose_ids = {item["id"] for item in self.config["poses"]}
        self.assertTrue(all(item["pose"] in pose_ids for item in renders))

    def test_machine_and_owner_judgment_are_separate(self) -> None:
        owner = self.config["owner_visual_judgment"]
        self.assertIsNone(owner["decision"])
        self.assertTrue(owner["machine_must_not_claim_visual_approval"])
        rejection = set(owner["required_rejection_checks"])
        self.assertTrue(
            {
                "plate_like",
                "petal_like",
                "separate_insert_like",
                "dark_cavity_like",
                "broken_pose_or_body_intersection",
            }.issubset(rejection)
        )
        self.assertIn("PENDING_OWNER_VISUAL_JUDGMENT", self.source)
        self.assertIn("machine_pass_is_not_owner_approval", self.source)

    def test_worker_is_inert_without_three_independent_unlocks(self) -> None:
        self.assertIn("explicit --execute-fresh-reopen flag is required", self.source)
        self.assertIn("configuration is an unbound template", self.source)
        self.assertIn("execution remains disabled", self.source)
        self.assertIn("binding is deferred/null", self.source)
        self.assertIn("output bindings remain deferred/null", self.source)

    def test_template_refusal_executes_before_any_blender_import(self) -> None:
        spec = importlib.util.spec_from_file_location("r23_deferred_verifier", WORKER_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaisesRegex(module.VerificationError, "explicit"):
            module.run(CONFIG_PATH, False)
        with self.assertRaisesRegex(module.VerificationError, "unbound template"):
            module.run(CONFIG_PATH, True)

    def test_worker_has_exact_binding_and_fresh_reopen_contract(self) -> None:
        required_fragments = (
            "build evidence does not bind the exact candidate",
            "build evidence does not preserve exact R19 source",
            "bpy.ops.wm.read_factory_settings(use_empty=True)",
            "bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)",
            'bpy.ops.wm.open_mainfile(filepath=str(paths["candidate"]), load_ui=False)',
            "source_unchanged",
            "candidate_unchanged",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.source)
        source_open = self.source.index(
            "bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)"
        )
        candidate_open = self.source.index(
            'bpy.ops.wm.open_mainfile(filepath=str(paths["candidate"]), load_ui=False)'
        )
        self.assertLess(source_open, candidate_open)

    def test_worker_contains_required_measurements_and_fail_closed_render_order(self) -> None:
        required_functions = {
            node.name
            for node in self.tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertTrue(
            {
                "exact_intersections",
                "mesh_topology",
                "seam_continuity",
                "patch_weights",
                "retained_surface_subset",
                "deformation_series",
                "contact_proxy",
                "render_owner_package",
                "output_manifest",
            }.issubset(required_functions)
        )
        gate_position = self.source.index("machine gate failed before rendering")
        render_position = self.source.index("renders = render_owner_package")
        self.assertLess(gate_position, render_position)

    def test_worker_has_no_blend_save_export_or_runtime_operation(self) -> None:
        forbidden = (
            "save_as_mainfile",
            "save_mainfile",
            "export_scene",
            "export_mesh",
            "runtime.activate",
            "publish_candidate(",
            "assign_candidate(",
        )
        lowered = self.source.lower()
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, lowered)

    def test_worker_uses_exclusive_append_only_writes(self) -> None:
        self.assertIn('with path.open("x"', self.source)
        self.assertIn("append-only output path already exists", self.source)
        self.assertIn("render directory must be inside evidence directory", self.source)

    def test_truth_boundary_does_not_overclaim_external_mesh_evidence(self) -> None:
        truth = " ".join(self.config["truth_boundary"]).lower()
        for term in (
            "biological function",
            "continence",
            "internal-organ simulation",
            "fertility",
            "pregnancy",
            "owner visual approval",
        ):
            self.assertIn(term, truth)


if __name__ == "__main__":
    unittest.main()
