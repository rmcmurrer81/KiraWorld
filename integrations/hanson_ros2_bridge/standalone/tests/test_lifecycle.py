from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "kira_hanson_bridge"
sys.path.insert(0, str(PACKAGE_ROOT))

from kira_hanson_bridge.lifecycle import (  # noqa: E402
    Capability,
    ClockRegression,
    DECISION_SCOPE,
    EmbodimentSession,
    IntentState,
    InvalidTransition,
    ProtocolError,
    RequestDisposition,
    SessionState,
    UnknownIntent,
    MAX_CANONICAL_PAYLOAD_BYTES,
)


class FakeClock:
    def __init__(self, value: int = 1_000) -> None:
        self.value = value

    def __call__(self) -> int:
        return self.value

    def advance(self, milliseconds: int) -> None:
        self.value += milliseconds


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()

    def session(
        self,
        *,
        capabilities: tuple[str, ...] = ("speech", "gaze", "expression", "gesture"),
        ttl_ms: int = 10_000,
        heartbeat_ms: int = 1_000,
    ) -> EmbodimentSession:
        return EmbodimentSession(
            session_id="opaque session / 7",
            body_id="body:little-sophia:sim",
            source_identity="identity:kira",
            capabilities=capabilities,
            session_ttl_ms=ttl_ms,
            heartbeat_timeout_ms=heartbeat_ms,
            now_ms=self.clock,
        )

    @staticmethod
    def request(
        session: EmbodimentSession,
        *,
        intent_id: str = "intent-1",
        sequence: int = 1,
        capability: str = "speech",
        payload: dict | None = None,
    ):
        return session.request_intent(
            intent_id=intent_id,
            sequence=sequence,
            capability=capability,
            payload=payload if payload is not None else {"text": "Hello."},
        )

    def test_session_preserves_opaque_identifiers_and_negotiated_capabilities(self) -> None:
        session = self.session(capabilities=("speech", "gesture", "speech"))
        snapshot = session.snapshot()

        self.assertEqual(snapshot.session_id, "opaque session / 7")
        self.assertEqual(snapshot.body_id, "body:little-sophia:sim")
        self.assertEqual(snapshot.source_identity, "identity:kira")
        self.assertEqual(snapshot.capabilities, {Capability.SPEECH, Capability.GESTURE})
        self.assertEqual(snapshot.state, SessionState.ACTIVE)
        self.assertEqual(snapshot.decision_scope, DECISION_SCOPE)

    def test_session_construction_rejects_bad_bounds_and_capabilities(self) -> None:
        base = dict(
            session_id="s",
            body_id="b",
            source_identity="i",
            capabilities=("speech",),
            session_ttl_ms=100,
            heartbeat_timeout_ms=10,
            now_ms=self.clock,
        )
        for field_name in ("session_id", "body_id", "source_identity"):
            with self.subTest(field=field_name), self.assertRaises(ProtocolError):
                EmbodimentSession(**{**base, field_name: " "})
        with self.assertRaises(ProtocolError):
            EmbodimentSession(**{**base, "session_ttl_ms": 0})
        with self.assertRaises(ProtocolError):
            EmbodimentSession(**{**base, "heartbeat_timeout_ms": True})
        with self.assertRaises(ProtocolError):
            EmbodimentSession(**{**base, "capabilities": ()})
        with self.assertRaises(ProtocolError):
            EmbodimentSession(**{**base, "capabilities": ("locomotion",)})

    def test_happy_path_records_requested_accepted_started_completed(self) -> None:
        session = self.session()
        result = self.request(session)
        self.assertEqual(result.disposition, RequestDisposition.ADMITTED)
        self.assertTrue(result.accepted)
        self.assertTrue(result.created)
        self.assertEqual(session.active_intent.state, IntentState.REQUESTED)

        self.clock.advance(1)
        session.accept("intent-1")
        self.clock.advance(1)
        session.start("intent-1")
        self.clock.advance(1)
        completed = session.complete("intent-1", detail="Simulator action finished.")

        self.assertEqual(completed.state, IntentState.COMPLETED)
        self.assertTrue(completed.terminal)
        self.assertEqual(
            [event.state for event in completed.events],
            [
                IntentState.REQUESTED,
                IntentState.ACCEPTED,
                IntentState.STARTED,
                IntentState.COMPLETED,
            ],
        )
        self.assertEqual([event.at_ms for event in completed.events], [1000, 1001, 1002, 1003])
        self.assertEqual(completed.events[-1].detail, "Simulator action finished.")
        self.assertIsNone(session.active_intent)

    def test_all_alternate_terminal_paths_are_represented(self) -> None:
        cases = (
            (IntentState.REJECTED, (), "reject"),
            (IntentState.FAILED, ("accept",), "fail"),
            (IntentState.CANCELLED, ("accept", "start"), "cancel"),
            (IntentState.INTERRUPTED, ("accept", "start"), "interrupt"),
            (IntentState.EXPIRED, ("accept",), "expire"),
        )
        for index, (terminal, setup_calls, terminal_call) in enumerate(cases, start=1):
            with self.subTest(terminal=terminal):
                session = self.session()
                intent_id = f"terminal-{index}"
                self.request(session, intent_id=intent_id)
                for name in setup_calls:
                    getattr(session, name)(intent_id)
                snapshot = getattr(session, terminal_call)(intent_id)
                self.assertEqual(snapshot.state, terminal)
                self.assertTrue(snapshot.terminal)
                self.assertIsNone(session.active_intent)

    def test_invalid_skips_and_terminal_retransition_are_rejected(self) -> None:
        session = self.session()
        self.request(session)
        with self.assertRaises(InvalidTransition):
            session.start("intent-1")
        session.reject("intent-1")
        with self.assertRaises(InvalidTransition):
            session.accept("intent-1")
        with self.assertRaises(UnknownIntent):
            session.accept("not-known")

    def test_only_one_intention_can_be_in_flight(self) -> None:
        session = self.session()
        self.request(session, intent_id="first", sequence=3)

        busy = self.request(session, intent_id="second", sequence=4)
        self.assertFalse(busy.accepted)
        self.assertEqual(busy.reason_code, "INTENT_IN_FLIGHT")
        self.assertEqual(session.last_sequence, 3)

        session.reject("first")
        admitted = self.request(session, intent_id="second", sequence=4)
        self.assertTrue(admitted.created)

    def test_sequence_must_be_positive_monotonic_and_bool_is_not_an_integer(self) -> None:
        session = self.session()
        for invalid in (0, -1, True, 1.5):
            with self.subTest(sequence=invalid):
                result = self.request(session, intent_id=f"bad-{invalid}", sequence=invalid)
                self.assertEqual(result.reason_code, "INVALID_SEQUENCE")
        self.assertEqual(session.last_sequence, 0)

        self.request(session, intent_id="high", sequence=8)
        session.reject("high")
        stale = self.request(session, intent_id="stale", sequence=8)
        self.assertEqual(stale.reason_code, "SEQUENCE_NOT_MONOTONIC")
        self.assertEqual(session.last_sequence, 8)

    def test_exact_retry_is_suppressed_despite_object_key_order(self) -> None:
        session = self.session()
        original = self.request(
            session,
            payload={"text": "Hello", "options": {"voice": "default", "rate": 1}},
        )
        retry = self.request(
            session,
            payload={"options": {"rate": 1, "voice": "default"}, "text": "Hello"},
        )

        self.assertTrue(original.created)
        self.assertTrue(retry.accepted)
        self.assertTrue(retry.duplicate)
        self.assertEqual(retry.reason_code, "DUPLICATE_SUPPRESSED")
        self.assertEqual(len(session.intents()), 1)
        self.assertEqual(len(retry.intent.events), 1)

    def test_exact_retry_after_completion_does_not_execute_again(self) -> None:
        session = self.session()
        self.request(session)
        session.accept("intent-1")
        session.start("intent-1")
        session.complete("intent-1")

        retry = self.request(session)
        self.assertTrue(retry.duplicate)
        self.assertEqual(retry.intent.state, IntentState.COMPLETED)
        self.assertIsNone(session.active_intent)

    def test_reusing_intent_id_with_any_canonical_change_conflicts(self) -> None:
        variants = (
            {"sequence": 2},
            {"capability": "gesture", "payload": {"gesture": "wave"}},
            {"payload": {"text": "Different"}},
        )
        for variant in variants:
            with self.subTest(variant=variant):
                session = self.session()
                self.request(session)
                arguments = {
                    "intent_id": "intent-1",
                    "sequence": 1,
                    "capability": "speech",
                    "payload": {"text": "Hello."},
                    **variant,
                }
                conflict = self.request(session, **arguments)
                self.assertEqual(conflict.reason_code, "INTENT_ID_CONFLICT")
                self.assertFalse(conflict.accepted)

    def test_payload_is_json_only_and_snapshot_returns_a_copy(self) -> None:
        session = self.session()
        invalid_values = ({"bad": float("nan")}, {"bad": object()}, {1: "bad key"})
        for index, payload in enumerate(invalid_values):
            with self.subTest(payload=payload):
                result = self.request(session, intent_id=f"bad-{index}", payload=payload)
                self.assertEqual(result.reason_code, "INVALID_PAYLOAD")

        result = self.request(session, payload={"nested": {"value": 1}})
        first_copy = result.intent.payload
        first_copy["nested"]["value"] = 99
        self.assertEqual(session.get_intent("intent-1").payload["nested"]["value"], 1)

    def test_global_and_negotiated_capability_limits_are_distinct(self) -> None:
        session = self.session(capabilities=("speech",))
        unsupported = self.request(session, capability="locomotion")
        self.assertEqual(unsupported.reason_code, "CAPABILITY_NOT_SUPPORTED")
        not_negotiated = self.request(
            session,
            capability="gesture",
            payload={"gesture": "wave"},
        )
        self.assertEqual(not_negotiated.reason_code, "CAPABILITY_NOT_NEGOTIATED")
        self.assertEqual(len(session.intents()), 0)

    def test_session_ttl_expires_in_flight_intent_and_blocks_new_actions(self) -> None:
        session = self.session(ttl_ms=100, heartbeat_ms=100)
        self.request(session)
        session.accept("intent-1")
        self.clock.advance(100)

        snapshot = session.tick()
        self.assertEqual(snapshot.state, SessionState.EXPIRED)
        self.assertEqual(snapshot.reason_code, "SESSION_TTL_EXPIRED")
        expired = session.get_intent("intent-1")
        self.assertEqual(expired.state, IntentState.EXPIRED)
        self.assertEqual(expired.events[-1].reason_code, "SESSION_TTL_EXPIRED")
        blocked = self.request(session, intent_id="intent-2", sequence=2)
        self.assertEqual(blocked.reason_code, "SESSION_NOT_ACTIVE")

    def test_heartbeat_extends_liveness_but_never_session_ttl(self) -> None:
        session = self.session(ttl_ms=150, heartbeat_ms=50)
        self.clock.advance(49)
        self.assertTrue(session.heartbeat())
        self.clock.advance(49)
        self.assertEqual(session.tick().state, SessionState.ACTIVE)
        self.assertTrue(session.heartbeat())
        self.clock.advance(52)

        snapshot = session.tick()
        self.assertEqual(snapshot.state, SessionState.EXPIRED)
        self.assertEqual(snapshot.reason_code, "SESSION_TTL_EXPIRED")

    def test_heartbeat_timeout_interrupts_execution_and_cannot_reconnect(self) -> None:
        session = self.session(ttl_ms=500, heartbeat_ms=50)
        self.request(session)
        session.accept("intent-1")
        session.start("intent-1")
        self.clock.advance(50)

        snapshot = session.tick()
        self.assertEqual(snapshot.state, SessionState.DISCONNECTED)
        self.assertEqual(snapshot.reason_code, "HEARTBEAT_TIMEOUT")
        interrupted = session.get_intent("intent-1")
        self.assertEqual(interrupted.state, IntentState.INTERRUPTED)
        self.assertEqual(interrupted.events[-1].reason_code, "HEARTBEAT_TIMEOUT")
        self.assertFalse(session.heartbeat())
        blocked = self.request(session, intent_id="intent-2", sequence=2)
        self.assertEqual(blocked.reason_code, "SESSION_NOT_ACTIVE")

    def test_explicit_disconnect_interrupts_and_duplicate_remains_queryable(self) -> None:
        session = self.session()
        self.request(session)
        disconnected = session.disconnect(reason_code="TRANSPORT_LOST")

        self.assertEqual(disconnected.state, SessionState.DISCONNECTED)
        self.assertEqual(session.get_intent("intent-1").state, IntentState.INTERRUPTED)
        retry = self.request(session)
        self.assertTrue(retry.duplicate)
        self.assertEqual(retry.intent.state, IntentState.INTERRUPTED)
        new = self.request(session, intent_id="intent-2", sequence=2)
        self.assertEqual(new.reason_code, "SESSION_NOT_ACTIVE")

    def test_clock_regression_is_rejected(self) -> None:
        session = self.session()
        self.clock.advance(1)
        session.tick()
        self.clock.value -= 2
        with self.assertRaises(ClockRegression):
            session.tick()

    def test_session_and_intent_identifiers_are_bounded(self) -> None:
        with self.assertRaises(ProtocolError):
            EmbodimentSession(
                session_id="x" * 129,
                body_id="body",
                source_identity="kira",
                capabilities=("speech",),
                session_ttl_ms=1000,
                heartbeat_timeout_ms=100,
                now_ms=self.clock,
            )
        session = self.session()
        result = self.request(session, intent_id="x" * 129)
        self.assertEqual(result.reason_code, "INVALID_INTENT_ID")

    def test_payload_bytes_are_bounded(self) -> None:
        session = self.session()
        result = self.request(
            session,
            payload={"text": "x" * (MAX_CANONICAL_PAYLOAD_BYTES + 1)},
        )
        self.assertEqual(result.reason_code, "PAYLOAD_TOO_LARGE")

    def test_huge_integer_and_recursive_payload_fail_closed(self) -> None:
        session = self.session()
        huge = self.request(session, payload={"n": 10**10000})
        self.assertEqual(huge.reason_code, "INVALID_PAYLOAD")

        recursive: dict = {}
        recursive["self"] = recursive
        cycle = self.request(session, intent_id="intent-cycle", payload=recursive)
        self.assertEqual(cycle.reason_code, "INVALID_PAYLOAD")

    def test_heartbeat_timeout_cannot_exceed_hard_session_ttl(self) -> None:
        with self.assertRaises(ProtocolError):
            self.session(ttl_ms=100, heartbeat_ms=101)

    def test_execution_decisions_are_explicitly_scoped_to_the_body(self) -> None:
        session = self.session()
        requested = self.request(session)
        rejected = session.reject(
            "intent-1",
            reason_code="SIMULATOR_LIMIT",
            detail="The simulated body declined this physical action.",
        )

        self.assertEqual(requested.decision_scope, "physical_execution_only")
        self.assertEqual(rejected.decision_scope, "physical_execution_only")
        self.assertEqual(rejected.events[-1].decision_scope, "physical_execution_only")
        self.assertNotIn("memory", rejected.events[-1].reason_code.lower())


if __name__ == "__main__":
    unittest.main()
