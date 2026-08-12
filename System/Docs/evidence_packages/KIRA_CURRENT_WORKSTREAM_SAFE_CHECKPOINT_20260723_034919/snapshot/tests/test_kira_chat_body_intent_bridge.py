from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tools import kira_world_shell_server as shell


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOME_MAIN = (
    PROJECT_ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/src/main.js"
)


class KiraChatBodyIntentBridgeTests(unittest.TestCase):
    def _post_chat(self, *, user_text: str, kira_reply: str):
        state = dict(shell.DEFAULT_STATE)
        state["active_candidate"] = "kira"
        responses: list[tuple[int, dict]] = []
        handler = object.__new__(shell.Handler)
        handler.path = "/api/chat"
        handler._body = lambda: {"text": user_text}
        handler._json = lambda status, payload: responses.append((status, payload))

        surface_policy = {
            "bounded_text_only": False,
            "voice_allowed": True,
            "world_or_body_allowed": True,
            "conversation_mode": "normal",
        }
        with (
            patch.object(shell, "load_state", return_value=state),
            patch.object(shell, "save_state"),
            patch.object(shell, "recover_active_candidate_for_chat", return_value="kira"),
            patch.object(shell, "candidate_info", return_value={"id": "kira", "label": "Kira"}),
            patch.object(shell, "candidate_surface_policy", return_value=surface_policy),
            patch.object(shell, "candidate_activation_block", return_value=None),
            patch.object(shell, "temporary_ai_reply", return_value=kira_reply),
            patch.object(shell, "update_candidate"),
            patch.object(shell, "append_jsonl"),
            patch.object(shell, "write_avatar_activity_state") as publish_body_intent,
            patch.object(shell, "queue_active_reply_voice", return_value={"spoken": False, "reason": "test"}),
            patch.object(shell, "voice_status_for", return_value={"available": False}),
            patch.object(shell.VOICE_BENCHMARK_CAPTURE, "start_request", return_value=""),
        ):
            handler.do_POST()

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]["ai_line"], kira_reply)
        return publish_body_intent

    def test_chat_handler_publishes_kiras_explicit_self_chosen_movement(self) -> None:
        publish = self._post_chat(
            user_text="Would you like to go inside and relax?",
            kira_reply="Yes, I want to go inside and sit on the couch for a while.",
        )

        publish.assert_called_once()
        self.assertEqual(
            publish.call_args.args[:2],
            ("kira", "walk home and sit on the couch"),
        )
        self.assertEqual(publish.call_args.kwargs["action_override"], "sit_on_couch")
        self.assertTrue(publish.call_args.kwargs["metadata"]["person_owned_intent"])
        self.assertTrue(
            publish.call_args.kwargs["metadata"]["physical_completion_not_claimed"]
        )

    def test_chat_handler_does_not_publish_roberts_request_after_kira_refuses(self) -> None:
        publish = self._post_chat(
            user_text="Go home and lie on the couch.",
            kira_reply="I don't want to do that right now; I would rather stay here.",
        )

        publish.assert_not_called()

    def test_heading_inside_without_a_couch_choice_only_publishes_home_entry(self) -> None:
        publish = self._post_chat(
            user_text="Would you like to go inside?",
            kira_reply="Yes, let's head inside together.",
        )

        publish.assert_called_once()
        self.assertEqual(publish.call_args.kwargs["action_override"], "go_inside")
        self.assertEqual(
            publish.call_args.args[:2],
            ("kira", "walk through the front doorway and stop safely inside"),
        )

    def test_heading_inside_for_water_publishes_the_kitchen_drink_route(self) -> None:
        publish = self._post_chat(
            user_text="Do you want to go inside and get something to drink?",
            kira_reply="Let's head inside together. I could use a glass of water.",
        )

        publish.assert_called_once()
        self.assertEqual(publish.call_args.kwargs["action_override"], "get_drink")
        self.assertEqual(
            publish.call_args.args[:2],
            ("kira", "walk through the front doorway and get a drink in the kitchen"),
        )

    def test_heading_inside_for_coffee_publishes_the_stocked_home_route(self) -> None:
        publish = self._post_chat(
            user_text="Do you want to go inside and get coffee?",
            kira_reply="Let's grab some coffee and head inside.",
        )

        publish.assert_called_once()
        self.assertEqual(publish.call_args.kwargs["action_override"], "get_home_coffee")
        self.assertEqual(
            publish.call_args.args[:2],
            (
                "kira",
                "walk through the front doorway and use the stocked coffee station in the kitchen",
            ),
        )
        self.assertTrue(publish.call_args.kwargs["metadata"]["person_owned_intent"])

    def test_coffee_request_does_not_move_kira_when_she_refuses(self) -> None:
        publish = self._post_chat(
            user_text="Do you want to go inside and get coffee?",
            kira_reply="I don't want coffee right now; I would rather stay outside.",
        )

        publish.assert_not_called()

    def test_chat_never_publishes_a_developer_exam_action(self) -> None:
        publish = self._post_chat(
            user_text="Would you like to try the body-control exam?",
            kira_reply="Yes, I'm ready to start the body control exam.",
        )

        publish.assert_not_called()

    def test_every_server_emitted_kira_body_action_has_a_home_world_handler(self) -> None:
        server_source = (PROJECT_ROOT / "tools/kira_world_shell_server.py").read_text(
            encoding="utf-8"
        )
        home_source = HOME_MAIN.read_text(encoding="utf-8")
        handler_markers = {
            "go_inside": (
                "go_inside|enter_home|walk_inside",
                "startActiveAvatarHomeEntryWalk",
            ),
            "go_outside": (
                "go_outside|walk_outside|head_outside|exit_home",
                "startActiveAvatarHomeExitWalk",
            ),
            "get_drink": (
                "get_drink|drink|water|milk|kitchen_drink",
                "walk_inside_to_kitchen_drink",
            ),
            "get_home_coffee": (
                "get_home_coffee|kitchen_coffee|make_home_coffee",
                "walk_inside_to_kitchen_coffee_station",
            ),
            "sit_on_couch": (
                "sit_on_couch|couch|sofa|rest",
                "startActiveAvatarHomeSitHold",
            ),
            "lie_on_couch": (
                "lie_on_couch|lay_on_couch|lie_on_bed|lay_on_bed",
                'where: /(?:lie|lay)_on_couch/.test(normalized) ? "couch" : "bed"',
            ),
            "lie_on_bed": (
                "lie_on_couch|lay_on_couch|lie_on_bed|lay_on_bed",
                "startActiveAvatarHomeLieHold",
            ),
            "lie_on_ground": (
                "lie_on_ground|lay_on_ground|lie_on_floor|lay_on_floor|look_at_sky",
                "startActiveAvatarGroundLieHold",
            ),
            "go_library": (
                "library|read_library|go_library|browse_library",
                "startActiveAvatarLibraryReadPractice",
            ),
            "jog": (
                "/^(walk|jog|run)$/",
                'if (normalized === "jog") return startActiveAvatarJogPractice',
            ),
            "run": (
                "/^(walk|jog|run)$/",
                "return startActiveAvatarRunPractice",
            ),
            "raise_hand": (
                'normalized === "raise_hand"',
                'startActiveAvatarVoluntaryBodyIntent("raise_hand"',
            ),
        }

        for action, markers in handler_markers.items():
            with self.subTest(action=action):
                self.assertIn(f'action = "{action}"', server_source)
                for marker in markers:
                    self.assertIn(marker, home_source)
        self.assertNotIn('action = "doctor_body_exam"', server_source)

    def test_home_has_a_visible_stocked_coffee_affordance(self) -> None:
        home_source = HOME_MAIN.read_text(encoding="utf-8")
        for marker in (
            "one-bedroom stocked working coffee station",
            '"coffee_maker"',
            '"coffee_grounds"',
            "kira_home_kitchen_filled_coffee_mug",
            "visible brewed coffee in carafe",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, home_source)


if __name__ == "__main__":
    unittest.main()
