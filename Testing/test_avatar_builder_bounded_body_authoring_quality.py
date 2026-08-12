"""Focused generic checks for the bounded Avatar Builder QA contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "Avatar/avatar_builder/tooling/bounded_body_authoring_quality_contract_v1.json"
)
README = ROOT / "Avatar/avatar_builder/README.md"
DOC = (
    ROOT
    / "System/Docs/AVATAR_BUILDER_BOUNDED_BODY_AUTHORING_QA_v1_20260802.md"
)
REGISTRY = (
    ROOT / "Avatar/avatar_builder/tooling/reusable_method_registry_v1.json"
)


class AvatarBuilderBoundedBodyAuthoringQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.contract_text = CONTRACT.read_text(encoding="utf-8")
        self.doc = DOC.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")

    def test_contract_is_generic_qa_not_promoted_geometry(self) -> None:
        self.assertEqual(1, self.contract["schema_version"])
        self.assertEqual(
            "MANDATORY_GENERIC_AUTHORING_QA_NOT_A_SELECTABLE_GEOMETRY_METHOD",
            self.contract["status"],
        )
        promotion = self.contract["promotion_boundary"]
        self.assertFalse(promotion["selectable_reusable_method"])
        self.assertFalse(promotion["geometry_method_promoted"])
        self.assertTrue(promotion["reusable_method_promotion_gate_still_required"])
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual("LOCKED_NO_PROMOTED_METHODS", registry["status"])
        self.assertEqual([], registry["selectable_methods"])

    def test_private_and_person_specific_payloads_are_forbidden(self) -> None:
        privacy = self.contract["privacy_boundary"]
        for key, value in privacy.items():
            if key == "generic_method_may_reference_only_candidate_supplied_hash_bound_masks":
                self.assertTrue(value)
            else:
                self.assertFalse(value, key)
        lowered = (self.contract_text + self.doc).casefold()
        for forbidden in (
            "kira_profiled",
            "biological_robert",
            "private_owner_review/kira",
            "recoverysprint/continuation",
        ):
            self.assertNotIn(forbidden, lowered)
        self.assertIsNone(re.search(r"\b[0-9a-f]{64}\b", self.contract_text))

    def test_contract_contains_no_geometry_identity_or_media_payload_fields(self) -> None:
        keys: set[str] = set()

        def collect(value: object) -> None:
            if isinstance(value, dict):
                keys.update(str(key) for key in value)
                for item in value.values():
                    collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)

        collect(self.contract)
        for forbidden in (
            "vertices",
            "faces",
            "vertex_indices",
            "face_indices",
            "coordinates",
            "deltas",
            "morph_values",
            "measurements",
            "identity_profile",
            "texture_paths",
            "image_paths",
        ):
            self.assertNotIn(forbidden, keys)

    def test_whole_source_package_and_live_state_are_immutable(self) -> None:
        guards = self.contract["immutable_input_and_state_guards"]
        self.assertIn(
            "source_package_inventory",
            guards["required_project_relative_sha256_bindings"],
        )
        self.assertIn(
            "protected_live_state_baseline",
            guards["required_project_relative_sha256_bindings"],
        )
        self.assertFalse(guards["source_asset_may_be_opened_for_overwrite"])
        self.assertTrue(guards["source_package_must_rehash_exactly_before_and_after"])
        self.assertTrue(guards["protected_live_state_must_rehash_exactly_before_and_after"])

    def test_blender_51_arrays_and_both_action_storage_modes_are_required(self) -> None:
        digest = self.contract["blender_5_1_digest_compatibility"]
        self.assertTrue(digest["mesh_attribute_array_values_canonicalized_recursively"])
        self.assertEqual(
            "FAIL_CLOSED", digest["unknown_attribute_value_or_data_item_policy"]
        )
        self.assertEqual(
            {
                "legacy_action_fcurves",
                "layered_action_layers_strips_channelbags_fcurves",
            },
            set(digest["action_storage_modes"]),
        )
        self.assertFalse(digest["removing_action_checks_when_an_api_changes_allowed"])

    def test_append_only_failure_evidence_never_modifies_prior_attempts(self) -> None:
        policy = self.contract["append_only_failure_discipline"]
        self.assertTrue(policy["output_must_be_a_new_authorized_child"])
        self.assertFalse(policy["overwrite_or_append_to_preexisting_output_allowed"])
        self.assertTrue(
            policy[
                "failure_evidence_may_be_written_only_when_output_did_not_exist_at_process_start"
            ]
        )
        self.assertFalse(policy["mechanical_pre_authoring_failure_counts_as_visual_attempt"])

    def test_each_exact_mask_stage_must_add_zero_pairs(self) -> None:
        stages = self.contract["exact_mask_stage_attribution"]
        self.assertIn("index_set_sha256", stages["required_mask_bindings"])
        self.assertIn("changed_index_set_sha256", stages["required_stage_evidence"])
        self.assertIn("intersection_pairs_before_and_after", stages["required_stage_evidence"])
        self.assertFalse(stages["changed_vertices_outside_authorized_mask_union_allowed"])
        self.assertEqual(
            "new_pairs = after_pairs - permitted_before_pairs",
            stages["stage_pair_delta_formula"],
        )
        self.assertEqual(0, stages["new_pair_count_required_after_every_stage"])
        self.assertEqual(0, stages["final_rest_nonadjacent_pair_count_required_for_complete_candidate"])

    def test_collision_backoff_stays_local_and_does_not_claim_visual_pass(self) -> None:
        repair = self.contract["collision_aware_local_backoff"]
        self.assertTrue(repair["allowed_only_inside_responsible_authorized_mask"])
        self.assertTrue(repair["protected_core_derived_from_newly_intersecting_faces"])
        self.assertTrue(repair["bounded_edge_ring_falloff_required"])
        self.assertTrue(repair["pinned_boundary_must_remain_exact"])
        self.assertTrue(repair["zero_new_pairs_required"])
        self.assertTrue(repair["failure_after_bounded_passes_discards_staged_result"])
        self.assertTrue(repair["lowering_global_strength_alone_is_not_collision_proof"])
        self.assertTrue(repair["technical_zero_intersection_is_not_visual_approval"])

    def test_degree_labeled_knee_and_contact_evidence_is_complete(self) -> None:
        audits = self.contract["degree_labeled_pose_and_contact_audits"]
        expected = {
            f"{side}_knee_bend_{degrees}deg"
            for side in ("left", "right", "bilateral")
            for degrees in (30, 55, 80)
        }
        self.assertEqual(expected, set(audits["required_knee_states"]))
        for field in (
            "requested_angle_degrees",
            "measured_angle_degrees",
            "exact_nonadjacent_intersection_pair_delta",
            "support_contact_residual",
            "foot_support_status",
            "neutral_restoration_digest",
        ):
            self.assertIn(field, audits["required_per_state_evidence"])
        self.assertFalse(audits["generic_pose_name_is_sufficient"])
        self.assertFalse(audits["lying_or_seated_static_pose_is_accepted_natural_motion"])

    def test_two_visual_attempt_stop_and_visible_rejections_are_durable(self) -> None:
        stop = self.contract["bounded_visual_attempt_stop"]
        self.assertEqual(2, stop["maximum_visual_repairs_for_same_defect"])
        self.assertFalse(
            stop["restart_whole_body_or_general_framework_after_second_attempt_allowed"]
        )
        self.assertTrue(stop["remaining_defects_must_be_hash_bound_and_disclosed"])
        required_rejections = {
            "plate_like_or_layered_surface",
            "dark_or_pinched_knee_at_55_or_80_degrees",
            "rounded_knee_collapse",
            "new_posed_self_intersection",
            "floating_or_unsupported_feet",
            "rigid_or_overlapping_contact_limbs",
            "generic_or_mannequin_like_face_or_eyes",
            "simplified_or_flat_nail_plates",
        }
        self.assertTrue(
            required_rejections.issubset(
                set(self.contract["visual_reject_or_owner_decision_conditions"])
            )
        )
        self.assertFalse(
            self.contract["output_policy"]["technical_pass_may_override_visual_rejection"]
        )

    def test_pipeline_map_and_system_document_link_the_exact_contract(self) -> None:
        relative = "tooling/bounded_body_authoring_quality_contract_v1.json"
        self.assertIn(relative, self.readme)
        self.assertIn(
            "Avatar/avatar_builder/" + relative,
            self.doc,
        )
        self.assertIn("two-completed-visual", self.readme)
        self.assertIn("after_pairs - permitted_before_pairs", self.doc)


if __name__ == "__main__":
    unittest.main()
