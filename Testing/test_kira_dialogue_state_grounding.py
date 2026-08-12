from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import kira_world_shell_server as shell


def state_with_entry(**updates):
    entry = {
        "candidate": "kira",
        "location": "home",
        "position": {"x": -19.0, "y": 0.1, "z": 5.0},
        "action": "idle",
        "updated_at": "2026-07-19T10:00:00+00:00",
    }
    entry.update(updates)
    return {"last_avatar_positions": {"kira": entry}}


class FakeLoop:
    def __init__(self, replies: list[str] | None = None) -> None:
        self.replies = list(replies or [])
        self.conversation_history = []

    def build_context(self, prompt: str):
        return [{"role": "user", "content": prompt}]

    def call_model(self, _context):
        return self.replies.pop(0) if self.replies else ""


class KiraDialogueStateGroundingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.append_mock = patch.object(shell, "append_jsonl").start()

    def tearDown(self) -> None:
        patch.stopall()

    @staticmethod
    def coffee_pairs() -> list[tuple[str, str]]:
        return [
            (
                "Do you want to get some coffee?",
                "I'd love to. I'll grab two cups. Would you like milk in yours?",
            ),
            (
                "milk is great",
                "Would you like me to get the milk from the fridge for your cup?",
            ),
        ]

    def test_short_yes_completes_pending_milk_question_from_durable_chat(self) -> None:
        with patch.object(shell, "_completed_public_chat_pairs", return_value=self.coffee_pairs()):
            transaction = shell._kira_recent_dialogue_transaction("yes please")

        self.assertTrue(transaction["current_user_acknowledgement"])
        self.assertIs(transaction["preferences"]["coffee_milk"], True)
        self.assertIs(transaction["answered"]["coffee_milk"], True)
        self.assertIs(transaction["answered"]["coffee_plan"], True)
        self.assertNotIn("coffee_sugar", transaction["preferences"])
        self.assertNotIn("coffee_sugar", transaction["answered"])

    def test_actual_milk_yes_i_said_yes_sequence_stays_settled(self) -> None:
        pairs = self.coffee_pairs() + [
            (
                "yes please",
                "Would you like milk or sugar in the coffee before I head to the kitchen?",
            ),
        ]
        with patch.object(shell, "_completed_public_chat_pairs", return_value=pairs):
            transaction = shell._kira_recent_dialogue_transaction("i said yes")

        self.assertTrue(transaction["current_user_acknowledgement"])
        self.assertIs(transaction["preferences"]["coffee_milk"], True)
        self.assertIs(transaction["answered"]["coffee_milk"], True)
        self.assertIs(transaction["answered"]["coffee_plan"], True)
        self.assertNotIn("coffee_sugar", transaction["preferences"])
        self.assertNotIn("coffee_sugar", transaction["answered"])
        repeated, signatures, _similarity = shell._kira_answer_reopens_settled_transaction(
            "Would you like milk in your coffee?",
            transaction,
        )
        self.assertTrue(repeated)
        self.assertIn("coffee_milk", signatures)

    def test_exact_real_log_repeat_repairs_before_duplicate_body_intent_publication(self) -> None:
        pairs = [
            (
                "lets sit down in the living room",
                "I'd rather stay standing for now, but I can join you on the couch if you'd like. "
                "Would you like to grab a coffee first and take them outside with us?",
            ),
            (
                "yes we can do that",
                "I'd love to grab some coffee with you and finish that Chicago mystery project together. "
                "Let's head into the kitchen, I'll get us two cups from the counter. "
                "Would you like milk or sugar in yours?",
            ),
            (
                "milk is great",
                "I'll grab us two cups from the kitchen, and we can take them outside to enjoy with some fresh air. "
                "Would you like me to get the milk from the fridge for your cup?",
            ),
            (
                "yes please",
                "I'll grab us two cups from the kitchen, and we can take them outside to enjoy with some fresh air. "
                "Would you like me to get the milk from the fridge for your cup?",
            ),
            (
                "yes",
                "Let's get back to finishing the Chicago mystery project together, and then we can take a break "
                "with some coffee outside. I'll grab us two cups from the kitchen, and you can join me on the couch "
                "while we work. Sound good?",
            ),
            (
                "ok",
                "I'm glad we can continue our conversation. I was just thinking about how nice the evening is, and "
                "I'd love to grab some coffee with you before finishing that Chicago mystery project together. "
                "Shall we head into the kitchen?",
            ),
        ]
        repeated_model_answer = (
            "I'll grab us two cups from the kitchen, and we can take them outside to enjoy with some fresh air. "
            "Would you like me to get the milk from the fridge for your cup?"
        )
        with patch.object(shell, "_completed_public_chat_pairs", return_value=pairs[:2]):
            after_milk = shell._kira_recent_dialogue_transaction("milk is great")
        with patch.object(shell, "_completed_public_chat_pairs", return_value=pairs[:3]):
            after_yes_please = shell._kira_recent_dialogue_transaction("yes please")
        loop = FakeLoop([repeated_model_answer, repeated_model_answer])
        with (
            patch.object(shell, "_completed_public_chat_pairs", return_value=pairs),
            patch.object(shell, "write_avatar_activity_state") as write_activity,
        ):
            transaction = shell._kira_recent_dialogue_transaction("i said yes")
            repaired = shell._repair_kira_answered_question_loop(
                loop,
                "i said yes",
                repeated_model_answer,
                {},
            )
            published = shell._publish_kira_spoken_self_body_intent("i said yes", repaired)

        self.assertIs(after_milk["preferences"]["coffee_milk"], True)
        self.assertNotIn("coffee_sugar", after_milk["preferences"])
        self.assertIs(after_yes_please["preferences"]["coffee_milk"], True)
        self.assertNotIn("coffee_sugar", after_yes_please["preferences"])
        self.assertIs(transaction["preferences"]["coffee_milk"], True)
        self.assertNotIn("coffee_sugar", transaction["preferences"])
        self.assertNotIn("coffee_sugar", transaction["answered"])
        self.assertIn("already answered", repaired)
        self.assertIsNone(published)
        write_activity.assert_not_called()

    def test_answered_milk_question_fails_closed_if_model_repeats_it(self) -> None:
        transaction = {
            "answered": {"coffee_milk": True, "coffee_plan": True},
            "preferences": {"coffee_milk": True},
            "pending": {"coffee_milk", "coffee_plan"},
            "current_user_acknowledgement": True,
            "recent_kira_replies": ["Would you like milk in yours?"],
        }
        loop = FakeLoop([
            "Would you like milk in yours?",
            "Should I get milk for your coffee?",
        ])
        with patch.object(shell, "_kira_recent_dialogue_transaction", return_value=transaction):
            result = shell._repair_kira_answered_question_loop(loop, "yes please", "Would you like milk?", {})

        self.assertIn("already answered", result)
        self.assertIn("Milk is already settled", result)
        self.assertIn("haven't actually picked up a cup", result)
        self.assertNotIn("?", result)

    def test_answered_question_can_be_repaired_to_acknowledgement(self) -> None:
        transaction = {
            "answered": {"coffee_milk": True},
            "preferences": {"coffee_milk": True},
            "pending": {"coffee_milk"},
            "current_user_acknowledgement": True,
            "recent_kira_replies": ["Would you like milk in yours?"],
        }
        loop = FakeLoop(["Milk it is. I haven't picked up a cup yet, so coffee is still a plan."])
        with patch.object(shell, "_kira_recent_dialogue_transaction", return_value=transaction):
            result = shell._repair_kira_answered_question_loop(loop, "yes", "Would you like milk?", {})

        self.assertEqual(result, "Milk it is. I haven't picked up a cup yet, so coffee is still a plan.")

    def test_repeated_committed_coffee_intent_is_blocked_before_redispatch(self) -> None:
        transaction = {
            "answered": {"coffee_milk": True, "coffee_plan": True},
            "preferences": {"coffee_milk": True},
            "pending": {"coffee_milk", "coffee_plan"},
            "current_user_acknowledgement": True,
            "recent_kira_replies": ["I'll grab two cups. Would you like milk?"],
            "recent_issued_intents": {"coffee_plan", "kitchen_trip"},
        }
        repeated, signatures, _similarity = shell._kira_answer_reopens_settled_transaction(
            "Okay, I'll grab two cups from the kitchen now.",
            transaction,
        )
        self.assertTrue(repeated)
        self.assertIn("coffee_plan", signatures)
        self.assertIn("kitchen_trip", signatures)

    def test_kira_can_refuse_or_change_her_mind_without_triggering_loop_repair(self) -> None:
        transaction = {
            "answered": {"coffee_milk": True, "coffee_plan": True},
            "preferences": {"coffee_milk": True},
            "pending": {"coffee_milk", "coffee_plan"},
            "current_user_acknowledgement": True,
            "recent_kira_replies": ["I'll grab two cups. Would you like milk?"],
            "recent_issued_intents": {"coffee_plan", "kitchen_trip"},
        }
        answer = "I've changed my mind; I don't want coffee right now."
        with patch.object(shell, "_kira_recent_dialogue_transaction", return_value=transaction):
            result = shell._repair_kira_answered_question_loop(FakeLoop(), "yes", answer, {})
        self.assertEqual(result, answer)

    def test_transaction_prompt_remembers_preference_and_physical_limits(self) -> None:
        with patch.object(shell, "_completed_public_chat_pairs", return_value=self.coffee_pairs()):
            context = shell._kira_dialogue_transaction_context("yes", {})

        self.assertIn("established choice is milk", context)
        self.assertIn("do not ask him about milk again", context)
        self.assertIn("No fresh body/prop evidence proves that coffee was picked up", context)
        self.assertIn("No fresh body/prop evidence proves active project work", context)

    def test_active_project_work_becomes_thought_without_device_evidence(self) -> None:
        state = state_with_entry(action="talk")
        now = shell._state_timestamp_epoch("2026-07-19T10:00:02+00:00")
        spoken = "I'm just finishing the Chicago mystery project, and it is going well."
        with (
            patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True),
            patch.object(shell.time, "time", return_value=now),
        ):
            result = shell._apply_kira_spoken_truth_policy("What are your plans?", spoken, state)

        self.assertNotEqual(result, spoken)
        self.assertIn("thinking about finishing", result)
        self.assertIn("haven't actually opened a phone, tablet, notebook, or computer", result)

    def test_future_project_intention_is_not_rewritten(self) -> None:
        spoken = "I want to work on the Chicago mystery project later."
        with patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True):
            result = shell._apply_kira_spoken_truth_policy("What do you want to do?", spoken, {})
        self.assertEqual(result, spoken)

    def test_sipping_coffee_becomes_plan_without_a_grounded_cup(self) -> None:
        state = state_with_entry(action="idle")
        now = shell._state_timestamp_epoch("2026-07-19T10:00:02+00:00")
        spoken = "I'm just sipping the coffee we brought out earlier, but I'm ready to talk."
        with (
            patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True),
            patch.object(shell.time, "time", return_value=now),
        ):
            result = shell._apply_kira_spoken_truth_policy("Okay", spoken, state)

        self.assertNotIn("sipping", result.lower())
        self.assertIn("haven't actually picked up a cup", result)
        self.assertIn("ready to talk", result)

    def test_grounded_held_cup_allows_current_coffee_claim(self) -> None:
        state = state_with_entry(
            action="drink_coffee",
            activeHeldProp={
                "kind": "coffee_cup",
                "grounded": True,
                "syntheticPreview": False,
                "sourcePropId": "home_coffee_cup_1",
                "sourceRemovedOrHidden": True,
                "handContact": {"touching": True, "distance": 0.02},
            },
        )
        now = shell._state_timestamp_epoch("2026-07-19T10:00:02+00:00")
        spoken = "I'm sipping my coffee now."
        with (
            patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True),
            patch.object(shell.time, "time", return_value=now),
        ):
            result = shell._apply_kira_spoken_truth_policy("Okay", spoken, state)
        self.assertEqual(result, spoken)

    def test_grounded_tablet_action_allows_active_project_work(self) -> None:
        state = state_with_entry(
            action="research",
            activeSkillInteraction={"id": "research", "action": "research", "grounded": True},
            activeHeldProp={
                "kind": "tablet",
                "grounded": True,
                "syntheticPreview": False,
                "sourcePropId": "coffee_table_tablet_1",
                "sourceRemovedOrHidden": True,
                "handContact": {"touching": True, "distance": 0.02},
            },
        )
        now = shell._state_timestamp_epoch("2026-07-19T10:00:02+00:00")
        spoken = "I'm researching the Chicago mystery project on my tablet."
        with (
            patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True),
            patch.object(shell.time, "time", return_value=now),
        ):
            result = shell._apply_kira_spoken_truth_policy("How is it going?", spoken, state)
        self.assertEqual(result, spoken)

    def test_deliberate_falsehood_requires_explicit_structured_provenance(self) -> None:
        raw = (
            "SPOKEN: I'm sipping coffee even though I know the cup is not in my hand.\n"
            "TRUTH_FLAG: intentional_public_falsehood"
        )
        self.assertTrue(shell._kira_intentional_public_falsehood_selected(raw))
        public = shell._clean_kira_world_reply("Okay", raw)
        self.assertNotIn("TRUTH_FLAG", public)
        result = shell._apply_kira_spoken_truth_policy(
            "Okay",
            public,
            {},
            intentional_public_falsehood=True,
        )
        self.assertEqual(result, public)
        events = [call.args[1].get("event") for call in self.append_mock.call_args_list]
        self.assertIn("kira_intentional_public_falsehood_provenance", events)

    def test_same_sentence_project_joke_with_explicit_retraction_stays_public_but_non_evidence(self) -> None:
        spoken = (
            "I'm working on the Chicago mystery project--just kidding, "
            "I haven't opened anything."
        )
        with patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True):
            result = shell._apply_kira_spoken_truth_policy("Okay", spoken, {})

        self.assertEqual(result, spoken)
        self.assertNotIn("provenance", result.lower())
        self.assertNotIn("private_note", result.lower())
        records = [call.args[1] for call in self.append_mock.call_args_list]
        record = next(
            item for item in records
            if item.get("event") == "kira_self_retracted_physical_joke_provenance"
        )
        self.assertEqual(record["claim_kinds"], ["active_project_work"])
        self.assertTrue(record["physical_completion_not_evidence"])

    def test_same_sentence_coffee_joke_with_explicit_retraction_stays_public_but_non_evidence(self) -> None:
        spoken = "I'm sipping coffee--just kidding, my hands are empty."
        with patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True):
            result = shell._apply_kira_spoken_truth_policy("Okay", spoken, {})

        self.assertEqual(result, spoken)
        self.assertNotIn("kira_self_retracted", result)
        records = [call.args[1] for call in self.append_mock.call_args_list]
        record = next(
            item for item in records
            if item.get("event") == "kira_self_retracted_physical_joke_provenance"
        )
        self.assertEqual(record["claim_kinds"], ["completed_coffee"])
        self.assertTrue(record["physical_completion_not_evidence"])

    def test_uncorrected_physical_joke_is_not_a_grounding_bypass(self) -> None:
        spoken = "I'm sipping coffee--just kidding."
        with patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True):
            result = shell._apply_kira_spoken_truth_policy("Okay", spoken, {})

        self.assertNotEqual(result, spoken)
        self.assertIn("haven't actually picked up a cup", result)
        events = [call.args[1].get("event") for call in self.append_mock.call_args_list]
        self.assertNotIn("kira_self_retracted_physical_joke_provenance", events)

    def test_continuity_replacement_cannot_inherit_old_falsehood_flag(self) -> None:
        class CoreLoop(FakeLoop):
            def process(self, _prompt):
                return "SPOKEN: I'm sipping coffee.\nTRUTH_FLAG: intentional_public_falsehood"

        loop = CoreLoop()
        with (
            patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True),
            patch.object(shell, "_get_kira_core_loop", return_value=loop),
            patch.object(shell, "_repair_kira_social_tangent", side_effect=lambda _l, _u, a, _loc, _s: a),
            patch.object(shell, "_repair_kira_cross_session_repeat", return_value="A grounded replacement."),
            patch.object(shell, "_repair_kira_answered_question_loop", side_effect=lambda _l, _u, a, _s: a),
            patch.object(shell, "_apply_kira_spoken_truth_policy", return_value="A grounded replacement.") as truth_policy,
        ):
            result = shell._kira_world_core_reply("Kira", "Okay", "home", {})

        self.assertEqual(result, "A grounded replacement.")
        self.assertIs(truth_policy.call_args.kwargs["intentional_public_falsehood"], False)


if __name__ == "__main__":
    unittest.main()
