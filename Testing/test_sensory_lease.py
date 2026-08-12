from __future__ import annotations

import unittest

from Core.sensory_lease import SensoryLeaseError, issue_sensory_lease, validate_sensory_lease


class SensoryLeaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "s" * 64

    def test_exact_person_and_activation_round_trip(self) -> None:
        token = issue_sensory_lease(
            self.secret,
            person_id="kira",
            activation_revision="2026-08-01T20:00:00Z",
            ttl_seconds=90,
            clock=lambda: 1000.0,
            nonce="unit-nonce",
        )
        payload = validate_sensory_lease(
            token,
            self.secret,
            expected_person_id="kira",
            expected_activation_revision="2026-08-01T20:00:00Z",
            clock=lambda: 1089.0,
        )
        self.assertEqual(payload["person_id"], "kira")
        self.assertEqual(payload["nonce"], "unit-nonce")

    def test_wrong_person_revision_tamper_and_expiry_fail_closed(self) -> None:
        token = issue_sensory_lease(
            self.secret,
            person_id="lisa",
            activation_revision="rev-4",
            clock=lambda: 2000.0,
            nonce="unit-nonce",
        )
        invalid_cases = (
            dict(expected_person_id="kira", expected_activation_revision="rev-4", clock=lambda: 2001.0),
            dict(expected_person_id="lisa", expected_activation_revision="rev-5", clock=lambda: 2001.0),
            dict(expected_person_id="lisa", expected_activation_revision="rev-4", clock=lambda: 2090.0),
        )
        for kwargs in invalid_cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(SensoryLeaseError):
                validate_sensory_lease(token, self.secret, **kwargs)
        tampered = ("A" if token[0] != "A" else "B") + token[1:]
        with self.assertRaises(SensoryLeaseError):
            validate_sensory_lease(
                tampered,
                self.secret,
                expected_person_id="lisa",
                expected_activation_revision="rev-4",
                clock=lambda: 2001.0,
            )

    def test_empty_binding_short_secret_and_unbounded_ttl_are_rejected(self) -> None:
        for kwargs in (
            dict(secret=self.secret, person_id="", activation_revision="rev"),
            dict(secret=self.secret, person_id="kira", activation_revision=""),
            dict(secret="short", person_id="kira", activation_revision="rev"),
            dict(secret=self.secret, person_id="kira", activation_revision="rev", ttl_seconds=301),
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(SensoryLeaseError):
                issue_sensory_lease(**kwargs)


if __name__ == "__main__":
    unittest.main()

