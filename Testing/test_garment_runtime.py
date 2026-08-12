from __future__ import annotations

from copy import deepcopy
import json
import unittest

from Core.garment_contracts import (
    GarmentInstance,
    GarmentState,
    MaturityClass,
    OwnerScope,
    build_robe_definition,
)
from Core.garment_runtime import (
    CompatibilityError,
    DuplicateInstanceError,
    GarmentLedger,
    LedgerError,
    TransactionStatus,
    TransitionError,
)
from Testing.garment_test_support import (
    ACTOR_ID,
    ASSET_HASH,
    BODY_HASH,
    CONSENT_ID,
    ITEM_ID,
    MATURITY,
    RIG_HASH,
    SUBJECT_ID,
    WORLD_ID,
    anchor,
    robe_definition,
    valid_evidence,
)


class GarmentRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition = robe_definition()
        self.ledger = GarmentLedger([self.definition])
        self.ledger.register_instance(
            GarmentInstance(
                item_instance_id=ITEM_ID,
                garment_type_id=self.definition.garment_type_id,
                assigned_subject_id=SUBJECT_ID,
                body_owner_subject_id=SUBJECT_ID,
                maturity_class=MATURITY,
                state=GarmentState.HANGING_ON_HOOK,
                owner_scope=OwnerScope.WORLD,
                owner_id=WORLD_ID,
                location_anchor_id=anchor(self.definition, "world_wall_hook"),
            )
        )

    def begin(self, affordance_id: str, *, actor_id: str = ACTOR_ID):
        current = self.ledger.instance(ITEM_ID)
        return self.ledger.begin_transition(ITEM_ID, affordance_id, **self.begin_kwargs(current.revision, actor_id))

    def begin_kwargs(self, revision: int = 0, actor_id: str = ACTOR_ID) -> dict:
        return {
            "actor_id": actor_id,
            "expected_revision": revision,
            "asset_sha256": ASSET_HASH,
            "body_sha256": BODY_HASH,
            "rig_sha256": RIG_HASH,
            "subject_id": SUBJECT_ID,
            "body_owner_subject_id": SUBJECT_ID,
            "maturity_class": MATURITY,
            "consent": {
                "consent_record_id": CONSENT_ID,
                "subject_id": SUBJECT_ID,
                "decision": "consented",
                "revocable": True,
                "refusal_active": False,
            },
            "privacy": {
                "subject_id": SUBJECT_ID,
                "active": True,
                "observers_allowed": False,
                "log_scope": "evidence_only",
                "raw_visual_recording": False,
            },
            "target_world_id": WORLD_ID,
        }

    def pass_transition(self, affordance_id: str):
        transaction = self.begin(affordance_id)
        affordance = self.definition.affordance(affordance_id)
        evidence = valid_evidence(
            self.definition,
            affordance.evidence_gate,
            transaction.transaction_id,
        )
        decision = self.ledger.commit_transition(transaction.transaction_id, evidence)
        self.assertTrue(decision.passed, decision.reasons)
        return transaction

    def assert_single_view(self) -> None:
        views = self.ledger.inventory_views()
        ids = [item["item_instance_id"] for values in views.values() for item in values]
        self.assertEqual(ids, [ITEM_ID])
        self.assertEqual(ids.count(ITEM_ID), 1)

    def test_pending_transfer_keeps_world_item_until_atomic_commit(self) -> None:
        transaction = self.begin("take_from_hook")
        before = self.ledger.inventory_views()
        self.assertEqual([item["item_instance_id"] for item in before["world"]], [ITEM_ID])
        self.assertEqual(before["avatar"], [])

        evidence = valid_evidence(
            self.definition, "hook_detach", transaction.transaction_id
        )
        evidence["capture_basis"] = "timer_only"
        blocked = self.ledger.commit_transition(transaction.transaction_id, evidence)
        self.assertFalse(blocked.passed)
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)
        self.assertEqual(self.ledger.transaction(transaction.transaction_id).status, TransactionStatus.PENDING)
        self.assert_single_view()

        passed = self.ledger.commit_transition(
            transaction.transaction_id,
            valid_evidence(self.definition, "hook_detach", transaction.transaction_id),
        )
        self.assertTrue(passed.passed)
        item = self.ledger.instance(ITEM_ID)
        self.assertEqual(item.state, GarmentState.GRASPED_FROM_HOOK)
        self.assertEqual(item.owner_scope, OwnerScope.AVATAR)
        self.assertEqual(item.owner_id, ACTOR_ID)
        self.assertEqual(item.revision, 1)
        self.assert_single_view()

    def test_full_round_trip_preserves_one_instance_and_legal_states(self) -> None:
        journey = (
            ("take_from_hook", GarmentState.GRASPED_FROM_HOOK),
            ("thread_right_first", GarmentState.RIGHT_SLEEVE_THREADED),
            ("thread_left_second", GarmentState.BOTH_SLEEVES_THREADED),
            ("settle_shoulders", GarmentState.WORN_OPEN),
            ("move_worn_open", GarmentState.WORN_OPEN),
            ("tie_belt", GarmentState.WORN_TIED),
            ("move_worn_tied", GarmentState.WORN_TIED),
            ("untie_belt", GarmentState.WORN_OPEN),
            ("remove_robe", GarmentState.HELD_AFTER_REMOVAL),
            ("place_on_bed", GarmentState.PLACED_ON_BED),
            ("pick_up_placed_robe", GarmentState.HELD_AFTER_REMOVAL),
            ("throw_to_bed", GarmentState.THROWN_IN_FLIGHT),
            ("settle_after_throw", GarmentState.SETTLED_ON_BED),
            ("pick_up_placed_robe", GarmentState.HELD_AFTER_REMOVAL),
            ("rehang", GarmentState.HANGING_ON_HOOK),
        )
        for revision, (affordance_id, expected_state) in enumerate(journey, start=1):
            with self.subTest(affordance=affordance_id):
                self.pass_transition(affordance_id)
                item = self.ledger.instance(ITEM_ID)
                self.assertEqual(item.item_instance_id, ITEM_ID)
                self.assertEqual(item.state, expected_state)
                self.assertEqual(item.revision, revision)
                self.assert_single_view()
        final = self.ledger.instance(ITEM_ID)
        self.assertEqual(final.owner_scope, OwnerScope.WORLD)
        self.assertEqual(final.owner_id, WORLD_ID)
        self.assertEqual(final.location_anchor_id, anchor(self.definition, "world_wall_hook"))

    def test_left_arm_can_go_first(self) -> None:
        self.pass_transition("take_from_hook")
        self.pass_transition("thread_left_first")
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.LEFT_SLEEVE_THREADED)
        self.pass_transition("thread_right_second")
        self.pass_transition("settle_shoulders")
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.WORN_OPEN)

    def test_refusal_at_partial_sleeve_can_reverse_and_rehang_safely(self) -> None:
        self.pass_transition("take_from_hook")
        self.pass_transition("thread_right_first")
        pending_left = self.begin("thread_left_second")
        self.ledger.refuse_transition(
            pending_left.transaction_id,
            "subject chose to stop after one sleeve",
        )
        self.assertEqual(
            self.ledger.instance(ITEM_ID).state,
            GarmentState.RIGHT_SLEEVE_THREADED,
        )
        self.pass_transition("unthread_right_only")
        self.assertEqual(
            self.ledger.instance(ITEM_ID).state,
            GarmentState.GRASPED_FROM_HOOK,
        )
        self.pass_transition("rehang_after_partial_stop")
        final = self.ledger.instance(ITEM_ID)
        self.assertEqual(final.state, GarmentState.HANGING_ON_HOOK)
        self.assertEqual(final.owner_scope, OwnerScope.WORLD)
        self.assert_single_view()

    def test_both_sleeves_can_reverse_one_at_a_time(self) -> None:
        self.pass_transition("take_from_hook")
        self.pass_transition("thread_left_first")
        self.pass_transition("thread_right_second")
        self.pass_transition("unthread_right_from_both")
        self.assertEqual(
            self.ledger.instance(ITEM_ID).state,
            GarmentState.LEFT_SLEEVE_THREADED,
        )
        self.pass_transition("unthread_left_only")
        self.pass_transition("rehang_after_partial_stop")
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)

    def test_raw_trace_hash_is_bound_to_transaction_and_journal(self) -> None:
        transaction = self.begin("take_from_hook")
        evidence = valid_evidence(
            self.definition, "hook_detach", transaction.transaction_id
        )
        expected_hash = evidence["raw_trace_sha256"]
        decision = self.ledger.commit_transition(transaction.transaction_id, evidence)
        self.assertTrue(decision.passed)
        self.assertEqual(decision.raw_trace_sha256, expected_hash)
        stored = self.ledger.transaction(transaction.transaction_id)
        self.assertEqual(stored.last_evidence_trace_sha256, expected_hash)
        self.assertEqual(stored.last_evidence["raw_trace_sha256"], expected_hash)
        self.assertEqual(
            stored.last_evidence_context_sha256,
            decision.evidence_context_sha256,
        )
        self.assertEqual(stored.last_decision_sha256, decision.decision_sha256)
        journal = self.ledger.snapshot()["journal"]
        evaluated = [item for item in journal if item["event"] == "evidence_evaluated"]
        committed = [item for item in journal if item["event"] == "transition_committed"]
        self.assertEqual(evaluated[-1]["raw_trace_sha256"], expected_hash)
        self.assertEqual(committed[-1]["raw_trace_sha256"], expected_hash)
        self.assertEqual(
            evaluated[-1]["evidence_context_sha256"],
            decision.evidence_context_sha256,
        )
        self.assertEqual(
            committed[-1]["decision_sha256"],
            decision.decision_sha256,
        )
        persisted = json.dumps(self.ledger.snapshot(), sort_keys=True)
        self.assertNotIn('"hook_contact"', persisted)
        self.assertNotIn('"raw_trace":', persisted)

    def test_snapshot_rejects_deleted_reordered_or_tampered_journal(self) -> None:
        self.pass_transition("take_from_hook")
        source = self.ledger.snapshot()
        self.assertGreaterEqual(len(source["journal"]), 4)
        self.assertEqual(
            source["journal_binding"]["entry_count"],
            len(source["journal"]),
        )
        self.assertEqual(
            source["journal_binding"]["head_sha256"],
            source["journal"][-1]["entry_sha256"],
        )

        deleted = deepcopy(source)
        del deleted["journal"][1]
        with self.assertRaises(LedgerError):
            GarmentLedger.from_snapshot([self.definition], deleted)

        reordered = deepcopy(source)
        reordered["journal"][1], reordered["journal"][2] = (
            reordered["journal"][2],
            reordered["journal"][1],
        )
        with self.assertRaises(LedgerError):
            GarmentLedger.from_snapshot([self.definition], reordered)

        tampered = deepcopy(source)
        tampered["journal"][1]["event"] = "forged_transition"
        with self.assertRaises(LedgerError):
            GarmentLedger.from_snapshot([self.definition], tampered)

        wrong_head = deepcopy(source)
        wrong_head["journal_binding"]["head_sha256"] = "0" * 64
        with self.assertRaises(LedgerError):
            GarmentLedger.from_snapshot([self.definition], wrong_head)

    def test_duplicate_persistent_id_is_rejected(self) -> None:
        duplicate = GarmentInstance.from_dict(self.ledger.instance(ITEM_ID).to_dict())
        with self.assertRaises(DuplicateInstanceError):
            self.ledger.register_instance(duplicate)

    def test_direct_mutation_of_read_model_does_not_change_ledger(self) -> None:
        detached = self.ledger.instance(ITEM_ID)
        detached.state = GarmentState.PLACED_ON_BED
        detached.location_anchor_id = anchor(self.definition, "bed_surface")
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)

    def test_registration_deep_copies_caller_owned_instance(self) -> None:
        definition = robe_definition()
        ledger = GarmentLedger([definition])
        source = GarmentInstance(
            item_instance_id="caller_owned_robe",
            garment_type_id=definition.garment_type_id,
            assigned_subject_id=SUBJECT_ID,
            body_owner_subject_id=SUBJECT_ID,
            maturity_class=MATURITY,
            state=GarmentState.HANGING_ON_HOOK,
            owner_scope=OwnerScope.WORLD,
            owner_id=WORLD_ID,
            location_anchor_id=anchor(definition, "world_wall_hook"),
        )
        ledger.register_instance(source)
        source.state = GarmentState.PLACED_ON_BED
        source.location_anchor_id = anchor(definition, "bed_surface")
        self.assertEqual(
            ledger.instance("caller_owned_robe").state,
            GarmentState.HANGING_ON_HOOK,
        )

    def test_direct_mutation_of_transaction_read_model_does_not_change_ledger(self) -> None:
        transaction = self.begin("take_from_hook")
        transaction.status = TransactionStatus.COMMITTED
        self.assertEqual(
            self.ledger.transaction(transaction.transaction_id).status,
            TransactionStatus.PENDING,
        )
        detached = self.ledger.transaction(transaction.transaction_id)
        detached.status = TransactionStatus.COMMITTED
        self.assertEqual(
            self.ledger.transaction(transaction.transaction_id).status,
            TransactionStatus.PENDING,
        )

    def test_inventory_views_and_snapshots_are_detached(self) -> None:
        views = self.ledger.inventory_views()
        views["world"][0]["state"] = GarmentState.PLACED_ON_BED.value
        views["world"].clear()
        snapshot = self.ledger.snapshot()
        snapshot["instances"][0]["state"] = GarmentState.PLACED_ON_BED.value
        snapshot["journal"][0]["event"] = "tampered"
        snapshot["journal"].clear()
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)
        fresh = self.ledger.snapshot()
        self.assertEqual(fresh["journal"][0]["event"], "registered")
        self.assertEqual(len(fresh["journal"]), 1)

    def test_runtime_rejects_wrong_subject_maturity_consent_and_privacy(self) -> None:
        cases = []
        wrong_subject = self.begin_kwargs()
        wrong_subject["subject_id"] = "another_subject"
        cases.append((wrong_subject, CompatibilityError))
        wrong_owner = self.begin_kwargs()
        wrong_owner["body_owner_subject_id"] = "another_subject"
        cases.append((wrong_owner, CompatibilityError))
        wrong_maturity = self.begin_kwargs()
        wrong_maturity["maturity_class"] = MaturityClass.NON_ADULT_DOLL_SAFE
        cases.append((wrong_maturity, CompatibilityError))
        refused = self.begin_kwargs()
        refused["consent"]["decision"] = "refused"
        cases.append((refused, TransitionError))
        nonrevocable = self.begin_kwargs()
        nonrevocable["consent"]["revocable"] = False
        cases.append((nonrevocable, TransitionError))
        observed = self.begin_kwargs()
        observed["privacy"]["observers_allowed"] = True
        cases.append((observed, TransitionError))
        recorded = self.begin_kwargs()
        recorded["privacy"]["raw_visual_recording"] = True
        cases.append((recorded, TransitionError))
        for index, (kwargs, error) in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(error):
                    self.ledger.begin_transition(
                        ITEM_ID,
                        "take_from_hook",
                        **kwargs,
                    )
        self.assertEqual(self.ledger.instance(ITEM_ID).revision, 0)

    def test_evidence_refusal_or_privacy_failure_blocks_commit(self) -> None:
        transaction = self.begin("take_from_hook")
        evidence = valid_evidence(
            self.definition, "hook_detach", transaction.transaction_id
        )
        evidence["consent"]["refusal_active"] = True
        evidence["privacy"]["observers_allowed"] = True
        decision = self.ledger.commit_transition(transaction.transaction_id, evidence)
        self.assertFalse(decision.passed)
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)
        self.assertTrue(any("active refusal" in reason for reason in decision.reasons))
        self.assertTrue(any("observers" in reason for reason in decision.reasons))

    def test_unassigned_staged_definition_cannot_enter_runtime_inventory(self) -> None:
        staged = build_robe_definition(
            garment_type_id="unassigned_staged_robe",
            asset_sha256=ASSET_HASH,
            compatible_body_sha256=BODY_HASH,
            compatible_rig_sha256=RIG_HASH,
        )
        ledger = GarmentLedger([staged])
        with self.assertRaises(CompatibilityError):
            ledger.register_instance(
                GarmentInstance(
                    item_instance_id="unassigned_robe_instance",
                    garment_type_id=staged.garment_type_id,
                    assigned_subject_id="unassigned_subject",
                    body_owner_subject_id="unassigned_subject",
                    maturity_class=MaturityClass.UNASSIGNED_BLOCKED,
                    state=GarmentState.HANGING_ON_HOOK,
                    owner_scope=OwnerScope.WORLD,
                    owner_id=WORLD_ID,
                    location_anchor_id=anchor(staged, "world_wall_hook"),
                )
            )

    def test_exact_asset_body_and_rig_compatibility_is_enforced(self) -> None:
        fields = (
            {"asset_sha256": "d" * 64, "body_sha256": BODY_HASH, "rig_sha256": RIG_HASH},
            {"asset_sha256": ASSET_HASH, "body_sha256": "d" * 64, "rig_sha256": RIG_HASH},
            {"asset_sha256": ASSET_HASH, "body_sha256": BODY_HASH, "rig_sha256": "d" * 64},
        )
        for claims in fields:
            with self.subTest(claims=claims):
                with self.assertRaises(CompatibilityError):
                    self.ledger.begin_transition(
                        ITEM_ID,
                        "take_from_hook",
                        actor_id=ACTOR_ID,
                        expected_revision=0,
                        target_world_id=WORLD_ID,
                        subject_id=SUBJECT_ID,
                        body_owner_subject_id=SUBJECT_ID,
                        maturity_class=MATURITY,
                        consent={
                            "consent_record_id": CONSENT_ID,
                            "subject_id": SUBJECT_ID,
                            "decision": "consented",
                            "revocable": True,
                            "refusal_active": False,
                        },
                        privacy={
                            "subject_id": SUBJECT_ID,
                            "active": True,
                            "observers_allowed": False,
                            "log_scope": "evidence_only",
                            "raw_visual_recording": False,
                        },
                        **claims,
                    )
        self.assertEqual(self.ledger.instance(ITEM_ID).revision, 0)

    def test_illegal_state_transition_and_stale_revision_fail_closed(self) -> None:
        with self.assertRaises(TransitionError):
            self.begin("tie_belt")
        with self.assertRaises(TransitionError):
            self.ledger.begin_transition(
                ITEM_ID,
                "take_from_hook",
                actor_id=ACTOR_ID,
                expected_revision=99,
                asset_sha256=ASSET_HASH,
                body_sha256=BODY_HASH,
                rig_sha256=RIG_HASH,
                subject_id=SUBJECT_ID,
                body_owner_subject_id=SUBJECT_ID,
                maturity_class=MATURITY,
                consent={
                    "consent_record_id": CONSENT_ID,
                    "subject_id": SUBJECT_ID,
                    "decision": "consented",
                    "revocable": True,
                    "refusal_active": False,
                },
                privacy={
                    "subject_id": SUBJECT_ID,
                    "active": True,
                    "observers_allowed": False,
                    "log_scope": "evidence_only",
                    "raw_visual_recording": False,
                },
                target_world_id=WORLD_ID,
            )
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)

    def test_only_one_active_transaction_per_item(self) -> None:
        first = self.begin("take_from_hook")
        with self.assertRaises(TransitionError):
            self.begin("take_from_hook")
        self.ledger.cancel_transition(first.transaction_id, "operator cancelled preview")
        second = self.begin("take_from_hook")
        self.assertNotEqual(first.transaction_id, second.transaction_id)

    def test_suspend_and_resume_preserve_checkpoint(self) -> None:
        transaction = self.begin("take_from_hook")
        self.ledger.suspend_transition(transaction.transaction_id, "avatar requested a pause")
        self.assertEqual(self.ledger.transaction(transaction.transaction_id).status, TransactionStatus.SUSPENDED)
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)
        with self.assertRaises(TransitionError):
            self.ledger.commit_transition(
                transaction.transaction_id,
                valid_evidence(self.definition, "hook_detach", transaction.transaction_id),
            )
        self.ledger.resume_transition(transaction.transaction_id)
        decision = self.ledger.commit_transition(
            transaction.transaction_id,
            valid_evidence(self.definition, "hook_detach", transaction.transaction_id),
        )
        self.assertTrue(decision.passed)

    def test_refusal_is_terminal_and_does_not_move_or_duplicate_item(self) -> None:
        transaction = self.begin("take_from_hook")
        self.ledger.refuse_transition(transaction.transaction_id, "avatar chose not to wear it")
        stored = self.ledger.transaction(transaction.transaction_id)
        self.assertEqual(stored.status, TransactionStatus.REFUSED)
        self.assertEqual(stored.resolution_reason, "avatar chose not to wear it")
        self.assertEqual(self.ledger.instance(ITEM_ID).state, GarmentState.HANGING_ON_HOOK)
        self.assert_single_view()
        with self.assertRaises(TransitionError):
            self.ledger.resume_transition(transaction.transaction_id)

    def test_cancel_from_suspended_state_keeps_last_commit(self) -> None:
        transaction = self.begin("take_from_hook")
        self.ledger.suspend_transition(transaction.transaction_id, "pause")
        self.ledger.cancel_transition(transaction.transaction_id, "test ended")
        self.assertEqual(self.ledger.transaction(transaction.transaction_id).status, TransactionStatus.CANCELLED)
        self.assertEqual(self.ledger.instance(ITEM_ID).revision, 0)
        self.assert_single_view()

    def test_crash_recovery_rolls_back_pending_intent(self) -> None:
        transaction = self.begin("take_from_hook")
        snapshot = self.ledger.snapshot()
        restored = GarmentLedger.from_snapshot([self.definition], snapshot)
        item = restored.instance(ITEM_ID)
        self.assertEqual(item.state, GarmentState.HANGING_ON_HOOK)
        self.assertEqual(item.owner_scope, OwnerScope.WORLD)
        self.assertEqual(item.revision, 0)
        self.assertEqual(
            restored.transaction(transaction.transaction_id).status,
            TransactionStatus.RECOVERED_ROLLBACK,
        )
        ids = [
            value["item_instance_id"]
            for values in restored.inventory_views().values()
            for value in values
        ]
        self.assertEqual(ids, [ITEM_ID])

    def test_crash_recovery_rejects_duplicate_snapshot_items(self) -> None:
        snapshot = self.ledger.snapshot()
        snapshot["instances"].append(deepcopy(snapshot["instances"][0]))
        with self.assertRaises(DuplicateInstanceError):
            GarmentLedger.from_snapshot([self.definition], snapshot)

    def test_snapshot_rejects_tampered_transition_contract(self) -> None:
        self.begin("take_from_hook")
        snapshot = self.ledger.snapshot()
        snapshot["transactions"][0]["asset_sha256"] = "d" * 64
        with self.assertRaises(LedgerError):
            GarmentLedger.from_snapshot([self.definition], snapshot)

    def test_avatar_owned_garment_cannot_be_manipulated_by_another_actor(self) -> None:
        self.pass_transition("take_from_hook")
        with self.assertRaises(TransitionError):
            self.begin("thread_right_first", actor_id="different_avatar")
        item = self.ledger.instance(ITEM_ID)
        self.assertEqual(item.owner_id, ACTOR_ID)
        self.assertEqual(item.state, GarmentState.GRASPED_FROM_HOOK)

    def test_snapshot_round_trip_keeps_committed_state(self) -> None:
        committed = self.pass_transition("take_from_hook")
        restored = GarmentLedger.from_snapshot(
            [self.definition], self.ledger.snapshot()
        )
        self.assertEqual(restored.instance(ITEM_ID).state, GarmentState.GRASPED_FROM_HOOK)
        self.assertEqual(restored.instance(ITEM_ID).revision, 1)
        self.assertEqual(
            restored.transaction(committed.transaction_id).status,
            TransactionStatus.COMMITTED,
        )


if __name__ == "__main__":
    unittest.main()
