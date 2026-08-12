from __future__ import annotations

import unittest

from Core.garment_contracts import (
    AnchorSpec,
    ContractError,
    GarmentInstance,
    GarmentState,
    MaturityClass,
    OwnerScope,
    build_robe_definition,
    owner_scope_for_state,
)
from Testing.garment_test_support import (
    BODY_HASH,
    ITEM_ID,
    MATURITY,
    RIG_HASH,
    SUBJECT_ID,
    WORLD_ID,
    anchor,
    robe_definition,
)


class GarmentContractTests(unittest.TestCase):
    def test_robe_contract_has_structured_unique_anchors(self) -> None:
        definition = robe_definition()
        self.assertGreaterEqual(len(definition.anchors), 14)
        self.assertEqual(len({item.anchor_id for item in definition.anchors}), len(definition.anchors))
        providers = {item.provider for item in definition.anchors}
        self.assertEqual(providers, {"garment", "body", "world"})
        for item in definition.anchors:
            self.assertIsInstance(item.local_position_m, tuple)
            self.assertEqual(len(item.local_position_m), 3)
            self.assertGreater(item.interaction_radius_m, 0)

    def test_every_affordance_names_existing_anchor_roles(self) -> None:
        definition = robe_definition()
        roles = {item.role for item in definition.anchors}
        for affordance in definition.affordances:
            with self.subTest(affordance=affordance.affordance_id):
                self.assertTrue(set(affordance.required_anchor_roles) <= roles)
                self.assertTrue(affordance.evidence_gate)

    def test_either_sleeve_may_be_threaded_first_but_both_are_required(self) -> None:
        definition = robe_definition()
        right = definition.affordance("thread_right_first")
        left = definition.affordance("thread_left_first")
        settle = definition.affordance("settle_shoulders")
        self.assertEqual(right.from_states, (GarmentState.GRASPED_FROM_HOOK,))
        self.assertEqual(left.from_states, (GarmentState.GRASPED_FROM_HOOK,))
        self.assertEqual(settle.from_states, (GarmentState.BOTH_SLEEVES_THREADED,))

    def test_partial_sleeves_have_safe_reverse_paths(self) -> None:
        definition = robe_definition()
        self.assertEqual(
            definition.affordance("unthread_right_only").target_state,
            GarmentState.GRASPED_FROM_HOOK,
        )
        self.assertEqual(
            definition.affordance("unthread_left_only").target_state,
            GarmentState.GRASPED_FROM_HOOK,
        )
        self.assertEqual(
            definition.affordance("unthread_left_from_both").target_state,
            GarmentState.RIGHT_SLEEVE_THREADED,
        )
        self.assertEqual(
            definition.affordance("unthread_right_from_both").target_state,
            GarmentState.LEFT_SLEEVE_THREADED,
        )
        self.assertEqual(
            definition.affordance("rehang_after_partial_stop").from_states,
            (GarmentState.GRASPED_FROM_HOOK,),
        )

    def test_definition_binds_exact_subject_and_maturity_policy(self) -> None:
        definition = robe_definition()
        self.assertEqual(definition.compatible_subject_id, SUBJECT_ID)
        self.assertIs(definition.maturity_class, MaturityClass.ADULT)

    def test_world_and_avatar_states_have_unambiguous_ownership(self) -> None:
        for state in GarmentState:
            expected = OwnerScope.WORLD if state in {
                GarmentState.HANGING_ON_HOOK,
                GarmentState.PLACED_ON_BED,
                GarmentState.THROWN_IN_FLIGHT,
                GarmentState.SETTLED_ON_BED,
            } else OwnerScope.AVATAR
            self.assertIs(owner_scope_for_state(state), expected)

    def test_instance_rejects_state_owner_disagreement(self) -> None:
        with self.assertRaises(ContractError):
            GarmentInstance(
                item_instance_id=ITEM_ID,
                garment_type_id="unit_test_robe_v1",
                assigned_subject_id=SUBJECT_ID,
                body_owner_subject_id=SUBJECT_ID,
                maturity_class=MATURITY,
                state=GarmentState.HANGING_ON_HOOK,
                owner_scope=OwnerScope.AVATAR,
                owner_id=WORLD_ID,
                location_anchor_id="world_wall_hook",
            )

    def test_hashes_are_exact_lowercase_sha256(self) -> None:
        for bad_hash in ("", "a" * 63, "A" * 64, "not-a-hash"):
            with self.subTest(hash=bad_hash):
                with self.assertRaises(ContractError):
                    build_robe_definition(
                        garment_type_id="bad_robe",
                        asset_sha256=bad_hash,
                        compatible_body_sha256=BODY_HASH,
                        compatible_rig_sha256=RIG_HASH,
                    )

    def test_anchor_rejects_nonfinite_coordinates(self) -> None:
        with self.assertRaises(ContractError):
            AnchorSpec(
                anchor_id="bad",
                role="bad",
                provider="world",
                node_name="bad",
                local_position_m=(0.0, float("nan"), 0.0),
                interaction_radius_m=0.1,
            )

    def test_instance_round_trip_preserves_persistent_identity(self) -> None:
        definition = robe_definition()
        instance = GarmentInstance(
            item_instance_id=ITEM_ID,
            garment_type_id=definition.garment_type_id,
            assigned_subject_id=SUBJECT_ID,
            body_owner_subject_id=SUBJECT_ID,
            maturity_class=MATURITY,
            state=GarmentState.HANGING_ON_HOOK,
            owner_scope=OwnerScope.WORLD,
            owner_id=WORLD_ID,
            location_anchor_id=anchor(definition, "world_wall_hook"),
        )
        restored = GarmentInstance.from_dict(instance.to_dict())
        self.assertEqual(restored.item_instance_id, ITEM_ID)
        self.assertEqual(restored.to_dict(), instance.to_dict())


if __name__ == "__main__":
    unittest.main()
