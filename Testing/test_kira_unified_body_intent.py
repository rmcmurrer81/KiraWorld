from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from Core.avatar_activity_state import infer_avatar_action, write_avatar_activity_state  # noqa: E402
from tools import kira_world_shell_server, run_kira_life_day  # noqa: E402


HOME_MAIN = (
    PROJECT_ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/src/main.js"
)


class UnifiedKiraBodyIntentTests(unittest.TestCase):
    def test_life_loop_phrases_map_to_embodied_intents(self) -> None:
        self.assertEqual(infer_avatar_action("read_for_hours with a tablet"), "persistent_read")
        self.assertEqual(infer_avatar_action("creative writing on the tablet"), "creative_write")
        self.assertEqual(infer_avatar_action("rest on the couch"), "lie_on_couch")

    def test_action_override_is_explicit_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("Core.avatar_activity_state.STATE_ROOT", root):
                path = write_avatar_activity_state(
                    "kira",
                    "unrelated description",
                    action_override="Persistent_Read !",
                    metadata={"person_owned_intent": True},
                )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["action"], "persistent_read")
            self.assertTrue(payload["metadata"]["person_owned_intent"])

    def test_activity_state_write_preserves_exact_selected_kira_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("Core.avatar_activity_state.STATE_ROOT", root):
                path = write_avatar_activity_state(
                    "kira",
                    "quietly thinking",
                    source="test_activity_update",
                )
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("kira_provisional_body_r6.glb", payload["model_url"])
        self.assertEqual(payload["model_status"], "rigged_model_ready")

    def test_shell_profile_update_repairs_stale_kira_body_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp)
            (profiles / "kira.json").write_text(
                json.dumps(
                    {
                        "candidate_id": "kira",
                        "model_url": "/Avatar/models/temp_ai/kira/avatar.glb",
                        "model_status": "rigged_model_ready",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(kira_world_shell_server, "TEMP_AI_DIR", profiles):
                for source in (
                    "kira_world_shell_activate",
                    "kira_world_shell_activity_update",
                    "kira_world_shell_deactivate",
                ):
                    updated = kira_world_shell_server.update_candidate(
                        "kira",
                        action="idle",
                        source=source,
                    )
                    self.assertIn("kira_provisional_body_r6.glb", updated["model_url"])
                    self.assertEqual(updated["model_status"], "rigged_model_ready")

    def test_life_loop_choice_publishes_person_owned_body_intent(self) -> None:
        manager = Mock()
        with (
            patch.object(run_kira_life_day, "DailyLifeManager", return_value=manager),
            patch.object(run_kira_life_day, "write_avatar_activity_state") as publish,
        ):
            run_kira_life_day.record_daily_life_state(
                {"subject": "kira", "run_id": "test-run", "cycle": 4},
                "creative_write",
            )
        publish.assert_called_once()
        args, kwargs = publish.call_args
        self.assertEqual(args[:2], ("kira", "creative writing on the coffee-table tablet"))
        self.assertEqual(kwargs["action_override"], "creative_write")
        self.assertEqual(kwargs["source"], "supervised_life_loop_subject_choice")
        self.assertTrue(kwargs["metadata"]["person_owned_intent"])

    def test_body_intent_state_exposes_revision_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kira.json").write_text(
                json.dumps(
                    {
                        "action": "persistent_read",
                        "activity": "read_for_hours",
                        "source": "supervised_life_loop_subject_choice",
                        "updated_at": "2026-07-17T23:00:00+00:00",
                        "metadata": {"person_owned_intent": True},
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(kira_world_shell_server, "TEMP_AI_DIR", root):
                state = kira_world_shell_server.active_avatar_state("kira")
        self.assertEqual(state["active_action"], "persistent_read")
        self.assertEqual(state["active_intent_source"], "supervised_life_loop_subject_choice")
        self.assertTrue(state["active_intent_metadata"]["person_owned_intent"])

    def test_live_kira_model_is_loaded_only_when_profile_matches_hash_bound_selection(self) -> None:
        live_profile = json.loads(
            (PROJECT_ROOT / "Avatar/state/temp_ai/kira.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kira.json").write_text(json.dumps(live_profile), encoding="utf-8")
            with patch.object(kira_world_shell_server, "TEMP_AI_DIR", root):
                state = kira_world_shell_server.active_avatar_state("kira")
        self.assertIn("kira_provisional_body_r6.glb", state["active_model_url"])
        self.assertTrue(state["active_body_selection"]["enforced"])
        self.assertTrue(state["active_body_selection"]["valid"])
        self.assertEqual(
            state["active_body_selection"]["selected_model_sha256"],
            "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
        )

    def test_live_kira_model_fails_closed_when_profile_diverges_from_selection(self) -> None:
        live_profile = json.loads(
            (PROJECT_ROOT / "Avatar/state/temp_ai/kira.json").read_text(encoding="utf-8")
        )
        live_profile["model_url"] = "/Avatar/models/temp_ai/kira/avatar.glb"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kira.json").write_text(json.dumps(live_profile), encoding="utf-8")
            with patch.object(kira_world_shell_server, "TEMP_AI_DIR", root):
                state = kira_world_shell_server.active_avatar_state("kira")
        self.assertEqual(state["active_model_url"], "")
        self.assertFalse(state["active_body_selection"]["valid"])
        self.assertEqual(
            state["active_body_selection"]["reason"],
            "kira_profile_and_selection_model_mismatch_fail_closed",
        )

    def test_live_kira_model_fails_closed_when_selector_rejects_evidence(self) -> None:
        live_profile = json.loads(
            (PROJECT_ROOT / "Avatar/state/temp_ai/kira.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kira.json").write_text(json.dumps(live_profile), encoding="utf-8")
            with (
                patch.object(kira_world_shell_server, "TEMP_AI_DIR", root),
                patch.object(
                    kira_world_shell_server,
                    "resolve_kira_runtime_body_path",
                    side_effect=ValueError("tampered"),
                ),
            ):
                state = kira_world_shell_server.active_avatar_state("kira")
        self.assertEqual(state["active_model_url"], "")
        self.assertFalse(state["active_body_selection"]["valid"])
        self.assertEqual(
            state["active_body_selection"]["reason"],
            "kira_runtime_body_selection_invalid_fail_closed",
        )

    def test_avatar_delivery_rechecks_exact_live_kira_payload_hash(self) -> None:
        payload = b"exact live Kira body bytes"
        expected = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "Avatar" / "candidate" / "kira.glb"
            model.parent.mkdir(parents=True)
            model.write_bytes(payload)
            profiles = root / "profiles"
            profiles.mkdir()
            (profiles / "kira.json").write_text(
                json.dumps({"model_url": "/Avatar/candidate/kira.glb"}),
                encoding="utf-8",
            )
            with (
                patch.object(kira_world_shell_server, "ROOT", root),
                patch.object(kira_world_shell_server, "TEMP_AI_DIR", profiles),
                patch.object(
                    kira_world_shell_server,
                    "_validated_kira_runtime_model",
                    return_value=(
                        "http://127.0.0.1/Avatar/candidate/kira.glb",
                        {"valid": True, "selected_model_sha256": expected},
                    ),
                ),
            ):
                delivered = kira_world_shell_server._read_avatar_asset_bytes_with_kira_guard(model)
        self.assertEqual(delivered, payload)

    def test_avatar_delivery_blocks_changed_live_kira_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "Avatar" / "candidate" / "kira.glb"
            model.parent.mkdir(parents=True)
            model.write_bytes(b"changed after selection validation")
            profiles = root / "profiles"
            profiles.mkdir()
            (profiles / "kira.json").write_text(
                json.dumps({"model_url": "/Avatar/candidate/kira.glb"}),
                encoding="utf-8",
            )
            with (
                patch.object(kira_world_shell_server, "ROOT", root),
                patch.object(kira_world_shell_server, "TEMP_AI_DIR", profiles),
                patch.object(
                    kira_world_shell_server,
                    "_validated_kira_runtime_model",
                    return_value=(
                        "http://127.0.0.1/Avatar/candidate/kira.glb",
                        {"valid": True, "selected_model_sha256": "0" * 64},
                    ),
                ),
            ):
                with self.assertRaisesRegex(
                    kira_world_shell_server.KiraLiveAvatarDeliveryBlocked,
                    "kira_live_model_delivery_sha256_mismatch",
                ):
                    kira_world_shell_server._read_avatar_asset_bytes_with_kira_guard(model)

    def test_avatar_delivery_does_not_apply_kira_guard_to_other_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live_model = root / "Avatar" / "candidate" / "kira.glb"
            other_asset = root / "Avatar" / "wardrobe" / "robe.glb"
            live_model.parent.mkdir(parents=True)
            other_asset.parent.mkdir(parents=True)
            live_model.write_bytes(b"live")
            other_asset.write_bytes(b"robe")
            profiles = root / "profiles"
            profiles.mkdir()
            (profiles / "kira.json").write_text(
                json.dumps({"model_url": "/Avatar/candidate/kira.glb"}),
                encoding="utf-8",
            )
            with (
                patch.object(kira_world_shell_server, "ROOT", root),
                patch.object(kira_world_shell_server, "TEMP_AI_DIR", profiles),
                patch.object(kira_world_shell_server, "_validated_kira_runtime_model") as validate,
            ):
                delivered = kira_world_shell_server._read_avatar_asset_bytes_with_kira_guard(other_asset)
        self.assertEqual(delivered, b"robe")
        validate.assert_not_called()

    def test_browser_poll_and_no_random_kira_wandering_are_present(self) -> None:
        server_source = (PROJECT_ROOT / "tools/kira_world_shell_server.py").read_text(encoding="utf-8")
        world_source = HOME_MAIN.read_text(encoding="utf-8")
        self.assertIn('api("/api/body-intent")', server_source)
        self.assertIn('if path == "/api/body-intent":', server_source)
        self.assertIn('setInterval(refreshActiveBodyIntent, 2500)', server_source)
        self.assertIn('if (activeAvatarIsKiraLike()) return false;', world_source)
        self.assertIn('activeMarker.userData.roamPolicy = "person_owned_intent_only";', world_source)
        self.assertIn("lie_on_couch|lay_on_couch|lie_on_bed|lay_on_bed", world_source)
        self.assertIn('where: /(?:lie|lay)_on_couch/.test(normalized) ? "couch" : "bed"', world_source)
        self.assertIn('!usingRecovery && !activeMarker.userData.practiceRoute', world_source)
        self.assertIn('activeMarker.userData.kind = "body_load_blocked_fail_closed";', world_source)
        self.assertIn('activeMarkerChildCount: activeMarker?.children?.length || 0,', world_source)

    def test_tablet_work_routes_from_current_position_without_teleport(self) -> None:
        source = HOME_MAIN.read_text(encoding="utf-8")
        self.assertIn('routeId: `walk_to_home_tablet_${mode}`', source)
        self.assertIn("return routeActiveAvatarToHomeHold(holdSpec", source)
        self.assertIn("Always begin from the body's actual current position", source)

    def test_kira_explicit_choice_to_head_inside_does_not_invent_a_couch_choice(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Do you want to go in the house and relax?",
            "I'd love to take a break with you, Robert. Why don't we head inside together?",
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent["action"], "go_inside")

    def test_kira_choice_to_head_inside_for_water_keeps_the_drink_destination(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Do you want to go inside and get something to drink?",
            "Let's head inside together. I could use a glass of water.",
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent["action"], "get_drink")

    def test_user_request_without_kira_agreement_never_moves_her(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Go home and lie on the couch.",
            "I don't want to do that right now; I would rather stay here.",
        )
        self.assertIsNone(intent)
        self.assertIsNone(
            kira_world_shell_server._infer_kira_spoken_self_body_intent(
                "Will you start the movement test?",
                "I will not start the movement test yet.",
            )
        )

    def test_unrelated_positive_reply_does_not_borrow_action_words_from_robert(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Would you rather lie on the grass or go home?",
            "I'd love to keep talking with you here for a while.",
        )
        self.assertIsNone(intent)

    def test_kira_can_choose_to_lie_on_supported_ground(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Would you rather go home or lie in the grass and look at the sky?",
            "I want to lie on the grass here and look at the sky for a while.",
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent["action"], "lie_on_ground")

    def test_latest_couch_wording_dispatches_kiras_own_choice(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "How are you? Do you want to take a seat on the couch?",
            (
                "How am I? I'm feeling pretty calm and relaxed right now, enjoying the quiet evening. "
                "You asked how I was doing, so I guess I'll just take a seat on the couch and unwind a bit."
            ),
        )

        self.assertIsNotNone(intent)
        self.assertEqual(intent["action"], "sit_on_couch")

    def test_latest_walk_wording_dispatches_kiras_own_exit_choice(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Let's go for a walk outside.",
            "I'm excited for our walk, Robert! Let's get comfortable before heading out.",
        )

        self.assertIsNotNone(intent)
        self.assertEqual(intent["action"], "go_outside")

    def test_outdoor_request_without_kiras_agreement_does_not_move_her(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Let's go for a walk outside.",
            "I would rather stay here and rest for now.",
        )

        self.assertIsNone(intent)

    def test_live_dialogue_never_starts_the_developer_body_control_harness(self) -> None:
        intent = kira_world_shell_server._infer_kira_spoken_self_body_intent(
            "Would you like to try the body-control exam?",
            "Yes, I'm ready to start the body control exam.",
        )
        self.assertIsNone(intent)

    def test_spoken_choice_publisher_marks_intent_person_owned_without_claiming_completion(self) -> None:
        with (
            patch.object(kira_world_shell_server, "write_avatar_activity_state") as publish,
            patch.object(kira_world_shell_server, "append_jsonl") as log,
        ):
            result = kira_world_shell_server._publish_kira_spoken_self_body_intent(
                "Do you want to go inside and relax?",
                "Yes, I want to go inside and take a break.",
            )
        self.assertEqual(result["action"], "go_inside")
        kwargs = publish.call_args.kwargs
        self.assertEqual(kwargs["action_override"], "go_inside")
        self.assertTrue(kwargs["metadata"]["person_owned_intent"])
        self.assertTrue(kwargs["metadata"]["physical_completion_not_claimed"])
        self.assertFalse(log.call_args.args[1]["physical_completion_claimed"])


if __name__ == "__main__":
    unittest.main()
