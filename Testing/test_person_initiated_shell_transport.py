from __future__ import annotations

import unittest
from unittest.mock import patch

from Core.shared_person_initiative import DecisionOpportunity, TurnTakingState
from tools import kira_world_shell_server as shell


class PersonInitiatedShellTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        shell.purge_person_initiative_runtime()

    def tearDown(self) -> None:
        shell.purge_person_initiative_runtime()

    @staticmethod
    def state(person_id: str = "kira", revision: str = "activation-person-event-1") -> dict:
        return {"active_candidate": person_id, "last_activation_at": revision}

    def publish_speech(self, state: dict, text: str = "I chose to say this on my own."):
        shell.activate_person_initiative_runtime(state)
        lease = shell.current_person_initiative_lease(state)
        self.assertIsNotNone(lease)
        decision = DecisionOpportunity(
            decision_id="initiative_shell_0001",
            person_id=lease.person_id,
            activation_revision=lease.activation_revision,
            pacing_profile_id=shell.initiative_pacing_profile(lease.person_id).profile_id,
            outcome="consider_speaking",
            initiative_score=0.8,
            speaking_pull=0.8,
            action_pull=0.2,
            reason_codes=("private_person_decision",),
            considered_cue_ids=(),
            excluded_own_tts_cue_ids=(),
            separate_input_turn_ids=(),
            turn_taking=TurnTakingState(),
        )
        shell.PERSON_EVENT_QUEUE.register_private_decision(lease, decision)
        return shell.PERSON_EVENT_QUEUE.publish_speech(
            lease,
            decision.decision_id,
            text,
        )

    def test_poll_displays_public_event_without_send_and_ack_queues_approved_voice(self) -> None:
        state = self.state()
        event = self.publish_speech(state)
        handler = object.__new__(shell.Handler)
        handler.path = "/api/person-events/poll"
        responses = []
        handler._json = lambda status, payload: responses.append((status, payload))
        with patch.object(shell, "load_state", return_value=state):
            handler.do_GET()
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]["events"][0]["event_id"], event.event_id)
        self.assertTrue(responses[0][1]["person_initiated_without_send_supported"])

        handler = object.__new__(shell.Handler)
        handler.path = "/api/person-events/ack"
        handler._body = lambda: {"event_id": event.event_id}
        responses = []
        handler._json = lambda status, payload: responses.append((status, payload))
        with (
            patch.object(shell, "load_state", return_value=state),
            patch.object(shell, "candidate_info", return_value={"label": "Kira"}),
            patch.object(
                shell,
                "queue_active_reply_voice",
                return_value={"spoken": False, "reason": "queued_async_voice"},
            ) as voice,
        ):
            handler.do_POST()
        self.assertTrue(responses[0][1]["acknowledged"])
        voice.assert_called_once_with("kira", "Kira", "I chose to say this on my own.")
        lease = shell.current_person_initiative_lease(state)
        self.assertEqual(shell.PERSON_EVENT_QUEUE.poll(lease), ())

    def test_person_switch_atomically_purges_old_public_events(self) -> None:
        old_state = self.state()
        self.publish_speech(old_state)
        new_state = self.state("lisa", "activation-person-event-2")
        status = shell.activate_person_initiative_runtime(new_state)
        self.assertEqual(status["person_id"], "lisa")
        lease = shell.current_person_initiative_lease(new_state)
        self.assertEqual(shell.PERSON_EVENT_QUEUE.poll(lease), ())

    def test_ui_polls_without_send_but_does_not_claim_generator_or_full_duplex(self) -> None:
        page = shell.html_shell().decode("utf-8")
        self.assertIn("pollPersonInitiatedEvents", page)
        self.assertIn('api("/api/person-events/poll")', page)
        self.assertIn('api("/api/person-events/ack"', page)
        status = shell.person_initiative_public_status({})
        self.assertFalse(status["model_generator_connected"])
        self.assertFalse(status["full_duplex_echo_subtraction_accepted"])
        self.assertTrue(status["supervised_acceptance_pending"])


if __name__ == "__main__":
    unittest.main()
