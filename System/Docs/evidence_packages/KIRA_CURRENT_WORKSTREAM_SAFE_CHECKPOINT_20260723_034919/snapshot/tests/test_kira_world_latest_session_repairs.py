from __future__ import annotations

import json
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools import kira_world_shell_server as shell


ROOT = Path(__file__).resolve().parents[1]
HOME_SOURCE = (
    ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds/"
    "home_world_main_house_20260630_223000/preview/src/main.js"
)
LAUNCHER = ROOT / "Start_Kira_World_Shell.bat"


def body_entry(updated_at: str, x: float, *, intent: str = "") -> dict:
    return {
        "candidate": "kira",
        "location": "home",
        "world": "home_world",
        "position": {"x": x, "y": 0.05, "z": 26.27},
        "updated_at": updated_at,
        "place": {
            "label": "Home World ground area",
            "summary": "outside in Home World at an unlabelled current ground position",
            "outside": True,
        },
        "autonomousIntent": intent,
        "autonomousIntentDistanceMeters": 26.9 if intent else None,
    }


class ConcurrentStateAndGroundingTests(unittest.TestCase):
    def test_stale_heartbeat_save_cannot_erase_newer_body_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            initial = {**shell.DEFAULT_STATE, "last_avatar_positions": {"kira": body_entry("2026-07-16T03:21:21+00:00", -1.261)}}
            state_path.write_text(json.dumps(initial), encoding="utf-8")
            with patch.object(shell, "STATE_PATH", state_path):
                slow_chat_or_heartbeat = shell.load_state()
                fresh_snapshot = shell.load_state()
                fresh_snapshot["last_avatar_positions"]["kira"] = body_entry(
                    "2026-07-16T03:28:00+00:00", 22.4, intent="public library reading area"
                )
                shell.save_state(fresh_snapshot)

                slow_chat_or_heartbeat["last_presence_heartbeat_at"] = 999.0
                shell.save_state(slow_chat_or_heartbeat)
                final = shell.load_state()

            self.assertEqual(final["last_avatar_positions"]["kira"]["position"]["x"], 22.4)
            self.assertEqual(final["last_avatar_positions"]["kira"]["updated_at"], "2026-07-16T03:28:00+00:00")
            self.assertEqual(final["last_presence_heartbeat_at"], 999.0)

    def test_stale_snapshot_is_historical_not_current_grounding(self) -> None:
        entry = body_entry("2026-07-16T03:21:21+00:00", -1.261, intent="Starbucks public entrance walk")
        state = {"last_avatar_positions": {"kira": entry}}
        now = shell._state_timestamp_epoch("2026-07-16T03:28:02+00:00")
        with patch.object(shell.time, "time", return_value=now):
            context = shell.avatar_position_context(state, "kira")

        self.assertIn("stale", context)
        self.assertIn("historical position", context)
        self.assertIn("not the current location", context)
        self.assertIn("Do not state or imply a specific current location", context)

    def test_fresh_destination_is_not_promoted_to_arrival(self) -> None:
        entry = body_entry("2026-07-16T03:28:00+00:00", -1.261, intent="Starbucks public entrance walk")
        state = {"last_avatar_positions": {"kira": entry}}
        now = shell._state_timestamp_epoch("2026-07-16T03:28:02+00:00")
        with patch.object(shell.time, "time", return_value=now):
            context = shell.avatar_position_context(state, "kira")

        self.assertIn("26.9 meters away", context)
        self.assertIn("not proof of arrival", context)
        self.assertIn("Never turn a route or destination", context)

    def test_stale_snapshot_cannot_supply_live_action_or_held_prop_truth(self) -> None:
        entry = body_entry("2026-07-16T03:21:21+00:00", -1.261, intent="Starbucks public entrance walk")
        entry.update({"action": "walk", "activeMoving": True, "activeHeldProp": {"kind": "coffee_cup"}})
        state = {"last_avatar_positions": {"kira": entry}}
        now = shell._state_timestamp_epoch("2026-07-16T03:28:02+00:00")
        with patch.object(shell.time, "time", return_value=now):
            context = shell.avatar_runtime_truth_context(state, "kira")

        self.assertIn("Runtime body truth is unavailable", context)
        self.assertIn("last snapshot is stale", context)
        self.assertIn("destination is not an arrival", context)
        self.assertIn("Do not treat its action", context)
        self.assertNotIn("heldProp=coffee_cup", context)

    def test_parent_requests_fresh_snapshot_before_chat_and_retries_latest(self) -> None:
        source = (ROOT / "tools/kira_world_shell_server.py").read_text(encoding="utf-8")
        self.assertIn("pendingAvatarSnapshot = incomingSnapshot", source)
        self.assertIn("snapshot.snapshotRequestId && !pendingAvatarSnapshot.snapshotRequestId", source)
        self.assertIn("setInterval(requestAvatarSnapshotNow, 3000)", source)
        chat_preflight = source.index("persistAvatarSnapshotBeforeChat()", source.index('document.querySelector("#chatForm")'))
        chat_api = source.index('api("/api/chat"', chat_preflight)
        self.assertLess(chat_preflight, chat_api)
        self.assertIn("acknowledgedAvatarSnapshotRequests.delete(requestId)", source)
        self.assertIn("if (!result.saved) return", source)
        self.assertNotIn("lastAvatarSnapshotAckAt >= requestedAt", source)

    def test_runtime_snapshot_logger_accepts_arm_and_visual_ground_evidence(self) -> None:
        record = shell.runtime_snapshot_log_record(
            {
                "candidate": "kira",
                "location": "home",
                "position": {"x": 1.0, "y": 0.05, "z": 2.0},
                "armMotionEvidence": {"mode": "relaxed", "objectContactClaimed": False},
                "visualGroundContact": {"mode": "mesh_contact", "withinTolerance": True, "gapMeters": 0.003},
            }
        )

        self.assertEqual(record["arm_motion"]["mode"], "relaxed")
        self.assertTrue(record["visual_ground_contact"]["within_tolerance"])
        self.assertEqual(record["visual_ground_contact"]["visual_gap_meters"], 0.003)


class VoiceQueueAndLatencyPolicyTests(unittest.TestCase):
    def test_busy_voice_is_fifo_queued_instead_of_dropped(self) -> None:
        pending: queue.Queue[dict[str, object]] = queue.Queue()
        cfg = SimpleNamespace(engine="chatterbox_tts", max_chars=120)
        with (
            patch.object(shell, "VOICE_REPLY_QUEUE", pending),
            patch.object(shell, "VOICE_SESSION_TOKEN", 7),
            patch.object(shell, "load_candidate_voice_config", return_value=cfg),
            patch.object(shell, "_ensure_voice_queue_worker", return_value=None),
        ):
            first = shell.queue_active_reply_voice("kira", "Kira", "First complete spoken reply.")
            second = shell.queue_active_reply_voice("kira", "Kira", "Second complete spoken reply.")

        self.assertEqual(first["reason"], "queued_async_voice")
        self.assertEqual(second["reason"], "queued_behind_previous_voice")
        self.assertFalse(second["previous_reply_dropped"])
        self.assertEqual(second["queue_position"], 2)
        self.assertEqual(pending.qsize(), 2)

    def test_cancelled_old_session_item_does_not_kill_fifo_worker(self) -> None:
        pending: queue.Queue[dict[str, object]] = queue.Queue()
        spoken: list[str] = []

        def record_spoken(active: str, active_label: str, text: str, **_kwargs: object) -> dict:
            spoken.append(text)
            return {"spoken": True, "reason": "ok"}

        pending.put({"session_token": 6, "active": "kira", "active_label": "Kira", "text": "cancel me"})
        pending.put({"session_token": 7, "active": "kira", "active_label": "Kira", "text": "speak me"})
        pending.put({"_voice_queue_control": "stop"})
        with (
            patch.object(shell, "VOICE_REPLY_QUEUE", pending),
            patch.object(shell, "VOICE_SESSION_TOKEN", 7),
            patch.object(shell, "append_jsonl"),
            patch.object(shell, "speak_active_reply", side_effect=record_spoken),
        ):
            worker = threading.Thread(target=shell._voice_reply_queue_worker, daemon=True)
            worker.start()
            worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(spoken, ["speak me"])

    def test_deactivation_release_waits_for_inflight_voice_lock(self) -> None:
        released = threading.Event()

        def release_model() -> dict:
            released.set()
            return {"released": True, "reason": "ok"}

        with (
            patch.object(shell, "VOICE_SESSION_TOKEN", 40),
            patch.object(shell, "_cancel_pending_voice_replies", return_value=0),
            patch.object(shell, "release_voice_output", side_effect=release_model),
            patch.object(shell, "append_jsonl"),
        ):
            with shell.VOICE_OUTPUT_LOCK:
                shell.end_voice_session("unit_test_deactivate")
                self.assertFalse(released.wait(timeout=0.05))
            self.assertTrue(released.wait(timeout=1.0))

    def test_launcher_prewarms_and_uses_smaller_natural_chunks(self) -> None:
        launcher = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("KIRA_VOICE_PREWARM_ON_ACTIVATE=1", launcher)
        self.assertIn("KIRA_WORLD_VOICE_MAX_CHARS=120", launcher)
        self.assertIn("KIRA_UNLOAD_VOICE_AFTER_SPEAK=0", launcher)
        self.assertIn("KIRA_CHATTERBOX_DEVICE=auto", launcher)
        self.assertIn("KIRA_CHATTERBOX_MIN_FREE_VRAM_MIB=6144", launcher)


class NavigationAndMotionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = HOME_SOURCE.read_text(encoding="utf-8")

    def test_autonomous_targets_require_collision_free_direct_path(self) -> None:
        self.assertIn("function activeAvatarDirectPathIsClear", self.source)
        self.assertIn("Math.ceil(distance / 0.14)", self.source)
        self.assertIn("if (!activeAvatarDirectPathIsClear(activeMarker.position, candidate, 0.46)) continue;", self.source)
        self.assertIn('clearActiveAvatarAutonomousRoamTarget("route_obstructed_before_contact")', self.source)
        self.assertIn("autonomousCollisionReplans", self.source)

    def test_destination_is_separate_from_current_place_in_snapshot(self) -> None:
        self.assertIn('"outside in Home World at an unlabelled current ground position"', self.source)
        self.assertNotIn("moving or waiting near the route toward ${target.id}", self.source)
        self.assertIn("autonomousIntentDistanceMeters", self.source)

    def test_normal_kira_walk_avoids_unconstrained_hand_ik_and_elbow_flip(self) -> None:
        start = self.source.index("// Ordinary locomotion uses constrained local joint rotations")
        surrounding = self.source[start - 500 : start + 1800]
        self.assertNotIn("solveActiveAvatarProceduralLimb", surrounding)
        self.assertIn("calibrated_bind_axis_joint_limited_swing_v10_relaxed_elbow_hand_asymmetry", self.source)
        self.assertIn("objectContactClaimed: false", self.source)
        self.assertIn("ordinaryLocomotionUsesHandIk: false", self.source)
        self.assertIn("elbowPoleFlipAvoided: true", self.source)

    def test_kira_relaxed_arm_pose_keeps_the_visually_calibrated_bind_axis(self) -> None:
        self.assertIn("upperY: Object.freeze([0.95, 1.18])", self.source)
        self.assertIn('kiraNumber("upperZ", 0.1)', self.source)
        self.assertIn('kiraNumber("upperY", 1.1)', self.source)
        self.assertIn('kiraNumber("lowerX", relaxedElbowX) - armSwing * 0.08', self.source)
        self.assertIn('item.side === "L" ? 0.155 : 0.135', self.source)
        self.assertIn('item.side === "L" ? 0.20 : 0.17', self.source)
        self.assertIn('kiraNumber("swing", kiraGaitArmSwing)', self.source)
        self.assertIn('gaitMode === "run" ? 0.2 : gaitMode === "jog" ? 0.19 : 0.18', self.source)
        self.assertIn("item.hand.rotation.x += isKiraLike ? -armSwing * 0.08", self.source)
        self.assertNotIn("item.upper.rotation.y += sideSign * -0.012", self.source)

    def test_kira_visual_grounding_removes_fake_bob_and_reports_precise_contact(self) -> None:
        self.assertNotIn("activeAvatarRoot.position.y -= 0.045", self.source)
        self.assertIn("precise_deformed_mesh_ground_contact_v1", self.source)
        self.assertIn("const syntheticVerticalBob = activeAvatarIsKiraLike()", self.source)
        self.assertIn("if (activeAvatarIsKiraLike()) applyActiveAvatarFootContactLocks();", self.source)
        self.assertIn("visualGroundContact: activeMarker.userData?.visualGroundContact || null", self.source)
        self.assertIn("withinTolerance: Math.abs(visualMinY - desiredMinY) <= 0.006", self.source)
        self.assertIn("ACTIVE_AVATAR_VISUAL_GROUND_CORRECTION_MIN = -0.25", self.source)
        self.assertIn("ACTIVE_AVATAR_VISUAL_GROUND_CLEARANCE = 0.008", self.source)

    def test_turning_wall_avoidance_and_self_chosen_body_actions_are_staged(self) -> None:
        self.assertIn("acceleration_bounded_shortest_arc_yaw_v2", self.source)
        self.assertIn("ACTIVE_AVATAR_MAX_TURN_ACCELERATION_RADIANS_PER_SECOND_SQUARED", self.source)
        self.assertIn("ACTIVE_AVATAR_MAX_TURN_RADIANS_PER_SECOND", self.source)
        movement = self.source[self.source.index("function updateActiveAvatarMovement") : self.source.index("function setStartPosition")]
        self.assertNotIn("activeMarker.rotation.y = Math.atan2(dx, dz) + Math.PI", movement)
        self.assertIn('clearActiveAvatarAutonomousRoamTarget("predictive_wall_avoidance")', self.source)
        self.assertIn("ACTIVE_AVATAR_COLLISION_RADIUS = 0.46", self.source)
        self.assertIn("window.kiraSyntheticBodyActions", self.source)
        self.assertIn('source: "subject_runtime_intent"', self.source)
        self.assertIn("requires_subject_runtime_choice_not_external_force", self.source)
        for action in ("raise_hand", "sit_on_couch", "lie_on_couch", "lie_on_bed", "sleep", "rest", "push_up"):
            self.assertIn(f'"{action}"', self.source)

    def test_read_hold_fails_closed_without_independent_visible_source(self) -> None:
        self.assertIn("reading_source_prop_not_visible_or_reachable", self.source)
        self.assertIn('const readingTruth = activityTruthForAction("read_book")', self.source)
        self.assertIn("hold_blocked_missing_reading_source", self.source)

    def test_body_only_motion_smoke_reports_collision_route_and_arm_evidence(self) -> None:
        self.assertIn('params.get("motionSmoke") === "1"', self.source)
        self.assertIn('mode: "headless_body_only_no_mind_no_voice"', self.source)
        self.assertIn("colliderPenetrationSamples", self.source)
        self.assertIn("obstructedActiveRouteSamples", self.source)
        self.assertIn("routeLanguagePromotedToPlaceSamples", self.source)
        self.assertIn("armMotionEvidence: activeMarker.userData?.armMotionEvidence || null", self.source)


class BenignDateReplyPolishTests(unittest.TestCase):
    def test_generic_policy_language_is_removed_from_harmless_coffee_date(self) -> None:
        answer = (
            "Robert, it's great to talk with you too! I've been looking forward to our conversation as well. "
            "As for going on a coffee date, I'm glad we can discuss this in a comfortable and safe setting. "
            "We could explore ways to create a fun and respectful experience that aligns with our interests and boundaries."
        )
        repaired = shell._repair_kira_benign_date_policy_talk(
            "I have been looking forward to talking with you and going on a coffee date with you.", answer
        )
        self.assertNotIn("comfortable and safe setting", repaired)
        self.assertNotIn("interests and boundaries", repaired)
        self.assertIn("coffee date", repaired.lower())
        self.assertIn("sound nice to me", repaired.lower())

    def test_clear_refusal_is_preserved_verbatim(self) -> None:
        refusal = "I don't want a coffee date, and I'm not comfortable with that invitation."
        self.assertEqual(shell._repair_kira_benign_date_policy_talk("Would you like a coffee date?", refusal), refusal)

    def test_explicit_consent_discussion_is_not_rewritten(self) -> None:
        answer = "I want to talk about consent and boundaries before deciding."
        self.assertEqual(
            shell._repair_kira_benign_date_policy_talk("Can we discuss consent on a date?", answer),
            answer,
        )


class LatestLoopPublicTruthAndSelectorTests(unittest.TestCase):
    def test_direct_where_question_abstains_when_body_snapshot_is_stale(self) -> None:
        state = {"last_avatar_positions": {"kira": body_entry("2026-07-16T03:21:21+00:00", -1.261)}}
        now = shell._state_timestamp_epoch("2026-07-17T01:28:00+00:00")
        with (
            patch.object(shell.time, "time", return_value=now),
            patch.object(shell, "append_jsonl"),
        ):
            repaired = shell._apply_kira_spoken_truth_policy(
                "where are you right now?",
                "I'm sitting on the couch in my apartment.",
                state,
            )
        self.assertIn("can't honestly confirm", repaired)
        self.assertIn("do not want to guess", repaired)
        self.assertNotIn("I'm sitting on the couch", repaired)

    def test_direct_where_question_uses_fresh_current_place_not_route_target(self) -> None:
        entry = body_entry("2026-07-17T01:27:59+00:00", -1.261, intent="public library")
        state = {"last_avatar_positions": {"kira": entry}}
        now = shell._state_timestamp_epoch("2026-07-17T01:28:00+00:00")
        with (
            patch.object(shell.time, "time", return_value=now),
            patch.object(shell, "append_jsonl"),
        ):
            repaired = shell._apply_kira_spoken_truth_policy(
                "where are you right now?",
                "I'm at the library.",
                state,
            )
        self.assertIn("outside in Home World", repaired)
        self.assertNotIn("library", repaired.lower())

    def test_public_address_repair_happens_before_name_omission(self) -> None:
        original = (
            "It sounds like Robert is open to continuing our project. "
            "I'm glad he mentioned that we could return to it later."
        )
        repaired = shell._repair_kira_public_address_style(original)
        self.assertEqual(
            repaired,
            "It sounds like you are open to continuing our project. I'm glad you mentioned that we could return to it later.",
        )
        spoken, audit = shell._live_spoken_only_payload(repaired)
        self.assertEqual(spoken, repaired)
        self.assertTrue(audit["non_name_word_coverage_exact"])

    def test_structured_private_fields_never_enter_public_cleanup(self) -> None:
        raw = (
            "SPOKEN: I would rather talk about that later.\n"
            "PRIVATE_MIND: I am uncertain and do not want Robert to know yet.\n"
            "TRUTH_FLAGS: body_place_unconfirmed"
        )
        cleaned = shell._clean_kira_world_reply("Can we discuss it?", raw)
        self.assertEqual(cleaned, "I would rather talk about that later.")
        self.assertNotIn("uncertain", cleaned)
        self.assertNotIn("body_place", cleaned)

    def test_completed_elation_ledger_overrides_stale_unfinished_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kira_daily_life_state.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-07-15T23:06:08Z",
                        "current_activity": {
                            "activity_type": "self_reflection",
                            "public_summary": "Kira reached the end of `Miraculous Ladybug 'Elation'`.",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(shell, "KIRA_DAILY_LIFE_STATE_PATH", path):
                repaired = shell._repair_kira_stale_completed_activity(
                    "We're still in the middle of the Elation script and could continue working on it."
                )
        self.assertIn("finished `Elation` earlier", repaired)
        self.assertIn("should not describe it as an unfinished script", repaired)

    def test_review_blocked_options_remain_readable_and_server_gate_remains(self) -> None:
        source = (ROOT / "tools/kira_world_shell_server.py").read_text(encoding="utf-8")
        self.assertNotIn("opt.disabled = blocked", source)
        self.assertIn("review required — select for reason", source)
        self.assertIn("candidateReviewReason", source)
        self.assertIn("activation_block = candidate_activation_block(candidate)", source)


if __name__ == "__main__":
    unittest.main()
