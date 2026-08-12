import json
import pickle
import sys
import unittest
from dataclasses import fields, replace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from shared_media_coview import (  # noqa: E402
    SharedMediaCoviewBinding,
    SharedMediaCoviewDecisionRequired,
    SharedMediaCoviewManager,
    SharedMediaCoviewNotFound,
)


class ManualClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class SharedMediaCoviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = ManualClock()
        self.manager = SharedMediaCoviewManager(
            clock=self.clock,
            default_ttl_seconds=5,
            confirmed_adult_participant_ids={"confirmed_adult_person"},
        )
        self.binding = SharedMediaCoviewBinding(
            person_id="non_adult_resident",
            activation_revision="activation-r7",
            session_nonce="opaque-session-nonce-123456",
            media_id="a" * 64,
        )

    def create(self, **kwargs):
        values = {
            "adult_participant_id": "robert_owner",
            "adult_decision": True,
        }
        values.update(kwargs)
        return self.manager.create(self.binding, **values)

    def test_robert_is_confirmed_but_explicit_true_is_still_required(self) -> None:
        with self.assertRaises(SharedMediaCoviewDecisionRequired):
            self.create(adult_decision=False)
        with self.assertRaises(SharedMediaCoviewDecisionRequired):
            self.create(adult_decision=1)
        with self.assertRaises(SharedMediaCoviewDecisionRequired):
            self.create(adult_participant_id="unconfirmed_person")

        receipt = self.create()
        status = self.manager.validate(
            receipt.token,
            self.binding,
            adult_participant_id="robert_owner",
        )
        self.assertTrue(status.active)
        self.assertEqual(status.adult_participant_id, "robert_owner")

    def test_every_activation_and_media_field_is_exactly_bound(self) -> None:
        receipt = self.create()
        changes = {
            "person_id": "different_resident",
            "activation_revision": "activation-r8",
            "session_nonce": "different-session-nonce-1234",
            "media_id": "b" * 64,
        }
        for field_name, value in changes.items():
            with self.subTest(field_name=field_name):
                with self.assertRaises(SharedMediaCoviewNotFound):
                    self.manager.validate(
                        receipt.token,
                        replace(self.binding, **{field_name: value}),
                        adult_participant_id="robert_owner",
                    )
        with self.assertRaises(SharedMediaCoviewNotFound):
            self.manager.validate(
                receipt.token,
                self.binding,
                adult_participant_id="confirmed_adult_person",
            )

    def test_refresh_slides_timeout_but_expiry_purges(self) -> None:
        receipt = self.create()
        self.clock.advance(4)
        refreshed = self.manager.refresh(
            receipt.token,
            self.binding,
            adult_participant_id="robert_owner",
        )
        self.assertEqual(refreshed.expires_in_seconds, 5)
        self.assertEqual(refreshed.refresh_count, 1)
        self.clock.advance(4)
        self.manager.validate(
            receipt.token,
            self.binding,
            adult_participant_id="robert_owner",
        )
        self.clock.advance(1)
        with self.assertRaises(SharedMediaCoviewNotFound):
            self.manager.validate(
                receipt.token,
                self.binding,
                adult_participant_id="robert_owner",
            )
        self.assertEqual(self.manager.active_count, 0)

    def test_participant_stop_revokes_without_unlocking_other_media(self) -> None:
        first = self.create()
        other_binding = replace(self.binding, media_id="c" * 64)
        other = self.manager.create(
            other_binding,
            adult_participant_id="confirmed_adult_person",
            adult_decision=True,
        )
        self.assertEqual(self.manager.purge_for_participant("robert_owner"), 1)
        with self.assertRaises(SharedMediaCoviewNotFound):
            self.manager.validate(
                first.token,
                self.binding,
                adult_participant_id="robert_owner",
            )
        self.manager.validate(
            other.token,
            other_binding,
            adult_participant_id="confirmed_adult_person",
        )

    def test_reclassification_purges_every_decision_for_only_that_exact_media(self) -> None:
        first = self.create()
        second = self.create()
        other_binding = replace(self.binding, media_id="c" * 64)
        other = self.manager.create(
            other_binding,
            adult_participant_id="robert_owner",
            adult_decision=True,
        )

        self.assertEqual(self.manager.purge_for_media_id(self.binding.media_id), 2)
        for receipt in (first, second):
            with self.assertRaises(SharedMediaCoviewNotFound):
                self.manager.validate(
                    receipt.token,
                    self.binding,
                    adult_participant_id="robert_owner",
                )
        self.manager.validate(
            other.token,
            other_binding,
            adult_participant_id="robert_owner",
        )

    def test_context_purge_covers_switch_media_change_stop_and_adult_exit(self) -> None:
        receipt = self.create()
        switched = replace(self.binding, activation_revision="activation-r8")
        self.assertEqual(
            self.manager.purge_invalid_context(
                active_binding=switched,
                participating_adult_ids={"robert_owner"},
            ),
            1,
        )
        with self.assertRaises(SharedMediaCoviewNotFound):
            self.manager.validate(
                receipt.token,
                self.binding,
                adult_participant_id="robert_owner",
            )

        media_changed = self.create()
        self.assertEqual(
            self.manager.purge_invalid_context(
                active_binding=replace(self.binding, media_id="d" * 64),
                participating_adult_ids={"robert_owner"},
            ),
            1,
        )
        adult_left = self.create()
        self.assertEqual(
            self.manager.purge_invalid_context(
                active_binding=self.binding,
                participating_adult_ids=set(),
            ),
            1,
        )
        stopped = self.create()
        self.assertEqual(
            self.manager.purge_invalid_context(
                active_binding=None,
                participating_adult_ids={"robert_owner"},
            ),
            1,
        )
        self.assertTrue(all((media_changed, adult_left, stopped)))

    def test_revoke_is_exact_and_snapshot_redacts_secrets(self) -> None:
        receipt = self.create()
        snapshot = self.manager.snapshot()
        self.assertEqual(snapshot.active_count, 1)
        self.assertEqual(len(snapshot.decisions), 1)
        status_field_names = {field.name for field in fields(snapshot.decisions[0])}
        self.assertNotIn("token", status_field_names)
        self.assertNotIn("session_nonce", status_field_names)
        self.assertNotIn(receipt.token, repr(receipt))
        self.assertNotIn(self.binding.session_nonce, repr(self.binding))
        for value in (self.binding, receipt, snapshot, snapshot.decisions[0], self.manager):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    pickle.dumps(value)
                with self.assertRaises(TypeError):
                    json.dumps(value)

        self.manager.revoke(
            receipt.token,
            self.binding,
            adult_participant_id="robert_owner",
        )
        self.assertEqual(self.manager.active_count, 0)
        with self.assertRaises(SharedMediaCoviewNotFound):
            self.manager.revoke(
                receipt.token,
                self.binding,
                adult_participant_id="robert_owner",
            )

    def test_decision_records_no_path_title_model_speech_or_person_mutation(self) -> None:
        receipt = self.create()
        status = self.manager.validate(
            receipt.token,
            self.binding,
            adult_participant_id="robert_owner",
        )
        all_fields = {
            field.name
            for value in (receipt, status, self.manager.snapshot())
            for field in fields(value)
        }
        for forbidden in (
            "path",
            "title",
            "model",
            "speech",
            "relationship",
            "memory",
            "maturity",
            "classification",
        ):
            self.assertNotIn(forbidden, all_fields)


if __name__ == "__main__":
    unittest.main()
