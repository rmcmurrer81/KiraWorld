from __future__ import annotations

from copy import deepcopy
import unittest

from Core.garment_evidence import evaluate_garment_transition
from Testing.garment_test_support import CONSENT_ID, ITEM_ID, robe_definition, valid_evidence


class GarmentEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition = robe_definition()

    def evaluate(self, affordance_id: str, evidence: dict, tx_id: str = "tx_evidence"):
        return evaluate_garment_transition(
            self.definition,
            self.definition.affordance(affordance_id),
            evidence,
            transaction_id=tx_id,
            item_instance_id=ITEM_ID,
            consent_record_id=CONSENT_ID,
        )

    def test_every_declared_gate_has_a_passing_physical_fixture(self) -> None:
        seen: set[str] = set()
        for affordance in self.definition.affordances:
            if affordance.evidence_gate in seen:
                continue
            seen.add(affordance.evidence_gate)
            tx_id = f"tx_{affordance.evidence_gate}"
            decision = self.evaluate(
                affordance.affordance_id,
                valid_evidence(self.definition, affordance.evidence_gate, tx_id),
                tx_id,
            )
            with self.subTest(gate=affordance.evidence_gate):
                self.assertTrue(decision.passed, decision.reasons)
                self.assertEqual(decision.status, "passed")
        self.assertEqual(seen, {item.evidence_gate for item in self.definition.affordances})

    def test_timer_or_state_name_can_never_be_success_evidence(self) -> None:
        affordance = self.definition.affordance("take_from_hook")
        evidence = valid_evidence(self.definition, affordance.evidence_gate, "tx_timer")
        evidence["capture_basis"] = "animation_elapsed"
        evidence["timer_only"] = True
        decision = self.evaluate("take_from_hook", evidence, "tx_timer")
        self.assertFalse(decision.passed)
        self.assertTrue(any("timer" in reason for reason in decision.reasons))

    def test_capture_basis_is_allowlisted_and_raw_trace_hash_is_verified(self) -> None:
        evidence = valid_evidence(self.definition, "hook_detach", "tx_trace")
        evidence["capture_basis"] = "custom_plugin_claim"
        decision = self.evaluate("take_from_hook", evidence, "tx_trace")
        self.assertFalse(decision.passed)
        self.assertTrue(any("approved runtime trace" in reason for reason in decision.reasons))

        evidence = valid_evidence(self.definition, "hook_detach", "tx_trace")
        evidence["raw_trace"]["frame_count"] = 999
        decision = self.evaluate("take_from_hook", evidence, "tx_trace")
        self.assertFalse(decision.passed)
        self.assertTrue(any("hash does not match" in reason for reason in decision.reasons))
        self.assertEqual(len(decision.raw_trace_sha256), 64)

    def test_negative_nonfinite_and_overlimit_contact_distances_fail(self) -> None:
        for value in (-0.01, float("nan"), float("inf"), 0.041):
            evidence = valid_evidence(self.definition, "hook_detach", "tx_distance")
            evidence["hook_contact"]["distance_m"] = value
            decision = self.evaluate("take_from_hook", evidence, "tx_distance")
            with self.subTest(value=value):
                self.assertFalse(decision.passed)
                self.assertTrue(any("contact distance" in reason for reason in decision.reasons))

    def test_hook_contact_requires_three_frames_under_four_centimeters(self) -> None:
        evidence = valid_evidence(self.definition, "hook_detach", "tx_contact_frames")
        evidence["hook_contact"]["consecutive_contact_frames"] = 2
        evidence["hook_contact"]["max_distance_m"] = 0.041
        decision = self.evaluate("take_from_hook", evidence, "tx_contact_frames")
        self.assertFalse(decision.passed)
        self.assertTrue(any("three consecutive" in reason for reason in decision.reasons))
        self.assertTrue(any("0.04" in reason for reason in decision.reasons))

    def test_same_raw_trace_cannot_identify_different_contact_results(self) -> None:
        passing_evidence = valid_evidence(
            self.definition, "hook_detach", "tx_complete_context"
        )
        failing_evidence = deepcopy(passing_evidence)
        failing_evidence["hook_contact"]["touching"] = False

        passing = self.evaluate(
            "take_from_hook", passing_evidence, "tx_complete_context"
        )
        failing = self.evaluate(
            "take_from_hook", failing_evidence, "tx_complete_context"
        )

        self.assertTrue(passing.passed)
        self.assertFalse(failing.passed)
        self.assertEqual(passing.raw_trace_sha256, failing.raw_trace_sha256)
        self.assertNotEqual(
            passing.evidence_context_sha256,
            failing.evidence_context_sha256,
        )
        self.assertNotEqual(passing.decision_sha256, failing.decision_sha256)
        for result in (passing.to_dict(), failing.to_dict()):
            self.assertNotIn("evidence", result)
            self.assertNotIn("raw_trace", result)
            self.assertEqual(len(result["evidence_context_sha256"]), 64)
            self.assertEqual(len(result["decision_sha256"]), 64)

    def test_evidence_is_bound_to_exact_transaction_and_item(self) -> None:
        evidence = valid_evidence(self.definition, "hook_detach", "different_tx")
        decision = self.evaluate("take_from_hook", evidence, "expected_tx")
        self.assertFalse(decision.passed)
        self.assertTrue(any("transaction" in reason for reason in decision.reasons))

        evidence = valid_evidence(self.definition, "hook_detach", "expected_tx")
        evidence["identity"]["target_instance_id"] = "duplicate_robe"
        decision = self.evaluate("take_from_hook", evidence, "expected_tx")
        self.assertFalse(decision.passed)
        self.assertTrue(any("target garment identity" in reason for reason in decision.reasons))

    def test_scene_duplication_blocks_transition(self) -> None:
        evidence = valid_evidence(self.definition, "hook_detach", "tx_duplicate")
        evidence["identity"]["matching_scene_nodes"] = 2
        evidence["detachment"]["source_copy_visible_after"] = True
        decision = self.evaluate("take_from_hook", evidence, "tx_duplicate")
        self.assertFalse(decision.passed)
        self.assertTrue(any("exactly one" in reason for reason in decision.reasons))
        self.assertTrue(any("source robe copy" in reason for reason in decision.reasons))

    def test_exact_asset_body_and_rig_hashes_are_required(self) -> None:
        cases = (
            ("asset_sha256", "d" * 64, "asset hash"),
            ("body_sha256", "d" * 64, "body hash"),
            ("rig_sha256", "d" * 64, "rig hash"),
        )
        for field, value, expected_reason in cases:
            evidence = valid_evidence(self.definition, "shoulder_settle", "tx_hash")
            evidence["identity"][field] = value
            decision = self.evaluate("settle_shoulders", evidence, "tx_hash")
            with self.subTest(field=field):
                self.assertFalse(decision.passed)
                self.assertTrue(any(expected_reason in reason for reason in decision.reasons))

    def test_subject_maturity_consent_and_privacy_are_exact_gates(self) -> None:
        mutations = (
            (("identity", "subject_id"), "another_subject", "garment subject"),
            (("identity", "body_owner_subject_id"), "another_subject", "body ownership"),
            (("identity", "maturity_class"), "non_adult_doll_safe", "maturity"),
            (("consent", "decision"), "refused", "did not consent"),
            (("consent", "refusal_active"), True, "active refusal"),
            (("privacy", "observers_allowed"), True, "observers"),
            (("privacy", "raw_visual_recording"), True, "imagery"),
        )
        for (section, field), value, expected_reason in mutations:
            evidence = valid_evidence(self.definition, "shoulder_settle", "tx_personhood")
            evidence[section][field] = value
            decision = self.evaluate("settle_shoulders", evidence, "tx_personhood")
            with self.subTest(section=section, field=field):
                self.assertFalse(decision.passed)
                self.assertTrue(any(expected_reason in reason for reason in decision.reasons))

    def test_hook_contact_must_precede_real_detachment(self) -> None:
        evidence = valid_evidence(self.definition, "hook_detach", "tx_hook")
        evidence["hook_contact"]["touching"] = False
        evidence["detachment"]["hand_contact_maintained"] = False
        decision = self.evaluate("take_from_hook", evidence, "tx_hook")
        self.assertFalse(decision.passed)
        self.assertTrue(any("hand contact" in reason for reason in decision.reasons))

    def test_sleeve_portal_crossing_requires_continuous_nonteported_path(self) -> None:
        evidence = valid_evidence(self.definition, "right_sleeve_crossing", "tx_sleeve")
        crossing = evidence["right_sleeve_crossing"]
        crossing["teleported"] = True
        crossing["segment_paths"]["forearm"]["continuous_path"] = False
        decision = self.evaluate("thread_right_first", evidence, "tx_sleeve")
        self.assertFalse(decision.passed)
        self.assertTrue(any("teleport" in reason for reason in decision.reasons))
        self.assertTrue(any("continuous" in reason for reason in decision.reasons))

    def test_sleeve_passage_requires_wrist_forearm_and_elbow(self) -> None:
        evidence = valid_evidence(self.definition, "left_sleeve_crossing", "tx_all_segments")
        del evidence["left_sleeve_crossing"]["segment_paths"]["elbow"]
        decision = self.evaluate("thread_left_first", evidence, "tx_all_segments")
        self.assertFalse(decision.passed)
        self.assertTrue(any("elbow" in reason for reason in decision.reasons))

    def test_shoulder_settle_needs_bilateral_support_and_collision_quality(self) -> None:
        evidence = valid_evidence(self.definition, "shoulder_settle", "tx_shoulders")
        evidence["shoulder_settle"]["right_supported"] = False
        evidence["shoulder_settle"]["max_collision_penetration_m"] = 0.20
        decision = self.evaluate("settle_shoulders", evidence, "tx_shoulders")
        self.assertFalse(decision.passed)
        self.assertTrue(any("both shoulders" in reason for reason in decision.reasons))
        self.assertTrue(any("clipping" in reason for reason in decision.reasons))

    def test_belt_tie_rejects_endpoint_substitution(self) -> None:
        evidence = valid_evidence(self.definition, "belt_tie", "tx_belt")
        evidence["belt_continuity"]["right_endpoint_instance_id"] = "fake_belt_end"
        evidence["belt_continuity"]["endpoint_substitution"] = True
        decision = self.evaluate("tie_belt", evidence, "tx_belt")
        self.assertFalse(decision.passed)
        self.assertTrue(any("right belt endpoint" in reason for reason in decision.reasons))
        self.assertTrue(any("substitution" in reason for reason in decision.reasons))

    def test_belt_tie_needs_sampled_crossing_and_tightening_not_a_pose_flag(self) -> None:
        evidence = valid_evidence(self.definition, "belt_tie", "tx_belt_static")
        evidence["belt_tie"].update(
            {
                "continuous_hand_paths": False,
                "knot_path_sample_count": 0,
                "wrap_crossing_count": 0,
                "tightening_displacement_m": 0.0,
            }
        )
        decision = self.evaluate("tie_belt", evidence, "tx_belt_static")
        self.assertFalse(decision.passed)
        self.assertTrue(any("sampled" in reason for reason in decision.reasons))
        self.assertTrue(any("tightening" in reason for reason in decision.reasons))

    def test_worn_movement_requires_grounded_displacement_and_rig_following(self) -> None:
        evidence = valid_evidence(self.definition, "worn_movement", "tx_move")
        evidence["worn_movement"]["walk"].update(
            {"displacement_m": 0.0, "grounded_route": False}
        )
        evidence["worn_movement"]["garment_follows_verified_rig"] = False
        decision = self.evaluate("move_worn_open", evidence, "tx_move")
        self.assertFalse(decision.passed)
        self.assertTrue(any("displacement" in reason for reason in decision.reasons))
        self.assertTrue(any("verified rig" in reason for reason in decision.reasons))

    def test_worn_movement_requires_turn_sit_stand_and_same_support(self) -> None:
        evidence = valid_evidence(self.definition, "worn_movement", "tx_postures")
        evidence["worn_movement"]["turn"]["rotation_degrees"] = 0.0
        evidence["worn_movement"]["sit"]["support_contact"] = False
        evidence["worn_movement"]["stand"]["seat_support_released"] = False
        evidence["worn_movement"]["support_continuity"]["stand_source_surface_instance_id"] = "different_chair"
        decision = self.evaluate("move_worn_open", evidence, "tx_postures")
        self.assertFalse(decision.passed)
        self.assertTrue(any("turn rotation" in reason for reason in decision.reasons))
        self.assertTrue(any("supported while seated" in reason for reason in decision.reasons))
        self.assertTrue(any("support was not released" in reason for reason in decision.reasons))
        self.assertTrue(any("same support surface" in reason for reason in decision.reasons))

    def test_removal_requires_both_outward_sleeve_crossings(self) -> None:
        evidence = valid_evidence(self.definition, "removal", "tx_remove")
        left_elbow = evidence["removal"]["left_sleeve_exit"]["segment_paths"]["elbow"]
        left_elbow["signed_distance_before_m"] = -0.06
        left_elbow["signed_distance_after_m"] = 0.06
        decision = self.evaluate("remove_robe", evidence, "tx_remove")
        self.assertFalse(decision.passed)
        self.assertTrue(any("removal path" in reason for reason in decision.reasons))

    def test_rehang_requires_hook_support_before_hand_release(self) -> None:
        evidence = valid_evidence(self.definition, "rehang", "tx_rehang")
        evidence["rehang"]["supported_by_hook"] = False
        evidence["rehang"]["hand_contact_until_attached"] = False
        decision = self.evaluate("rehang", evidence, "tx_rehang")
        self.assertFalse(decision.passed)
        self.assertTrue(any("supported" in reason for reason in decision.reasons))

    def test_bed_place_and_throw_are_distinct_physical_actions(self) -> None:
        placement = valid_evidence(self.definition, "bed_placement", "tx_place")
        placement["bed_placement"]["ballistic_throw"] = True
        self.assertFalse(self.evaluate("place_on_bed", placement, "tx_place").passed)

        release = valid_evidence(self.definition, "throw_release", "tx_throw")
        release["throw_release"]["physics_driven"] = False
        self.assertFalse(self.evaluate("throw_to_bed", release, "tx_throw").passed)

    def test_throw_settle_requires_continuity_contact_and_low_velocity(self) -> None:
        evidence = valid_evidence(self.definition, "throw_settle", "tx_settle")
        evidence["throw_settle"].update(
            {
                "continuous_from_release": False,
                "bed_collision_contact": False,
                "max_linear_speed_mps": 1.0,
            }
        )
        decision = self.evaluate("settle_after_throw", evidence, "tx_settle")
        self.assertFalse(decision.passed)
        self.assertTrue(any("continuity" in reason for reason in decision.reasons))
        self.assertTrue(any("moving" in reason for reason in decision.reasons))


if __name__ == "__main__":
    unittest.main()
