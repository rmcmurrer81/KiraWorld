from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import kira_world_shell_server as shell


def state_with_entry(**updates):
    entry = {
        "candidate": "kira",
        "location": "home",
        "position": {"x": -19.0, "y": 0.1, "z": 5.0},
        "action": "read_tablet",
        "updated_at": "2026-07-15T12:00:00+00:00",
    }
    entry.update(updates)
    return {"last_avatar_positions": {"kira": entry}}


class KiraWorldShellEmbodimentGroundingTests(unittest.TestCase):
    def setUp(self) -> None:
        # Spoken-truth helpers record private audit notes in production.  Unit
        # tests must never append their synthetic fixtures to Robert's live log.
        self._append_jsonl_patch = patch.object(shell, "append_jsonl")
        self._append_jsonl_patch.start()

    def tearDown(self) -> None:
        self._append_jsonl_patch.stop()

    def test_generated_held_tablet_is_not_physical_proof(self) -> None:
        state = state_with_entry(
            activeHeldProp={
                "kind": "tablet",
                "grounded": False,
                "syntheticPreview": True,
            },
            activeSkillInteraction={"id": "read_tablet"},
        )
        result = shell.tablet_body_grounding(state)
        self.assertFalse(result["physical_tablet_use_proven"])
        self.assertEqual(result["held_prop_kind"], "")

    def test_grounded_tablet_needs_source_continuity_and_hand_contact(self) -> None:
        state = state_with_entry(
            activeHeldProp={
                "kind": "tablet",
                "grounded": True,
                "syntheticPreview": False,
                "sourcePropId": "one_bedroom_tablet_001",
                "sourceRemovedOrHidden": True,
                "handContact": {"touching": True, "distance": 0.08},
            },
            activeSkillInteraction={"id": "read_tablet"},
        )
        result = shell.tablet_body_grounding(state)
        self.assertTrue(result["physical_tablet_use_proven"])
        self.assertEqual(result["held_prop_kind"], "tablet")

        state["last_avatar_positions"]["kira"]["activeHeldProp"].pop("sourcePropId")
        self.assertFalse(shell.tablet_body_grounding(state)["physical_tablet_use_proven"])

    def test_circular_held_preview_truth_is_rejected(self) -> None:
        state = state_with_entry(
            activeHeldProp={"kind": "tablet", "grounded": False, "syntheticPreview": True},
            activityTruthByAction={
                "use_phone": {
                    "grounded": True,
                    "evidence": [{"kind": "tablet", "label": "held tablet"}],
                },
            },
        )
        self.assertFalse(shell._entry_action_grounded(state, "kira", "use_phone"))

    def test_independent_nearby_prop_remains_availability_evidence(self) -> None:
        state = state_with_entry(
            activeHeldProp={"kind": "tablet", "grounded": False, "syntheticPreview": True},
            activityTruthByAction={
                "use_phone": {
                    "grounded": True,
                    "evidence": [
                        {"kind": "tablet", "label": "held tablet"},
                        {"kind": "tablet", "label": "Kira coffee-table tablet"},
                    ],
                },
            },
        )
        self.assertTrue(shell._entry_action_grounded(state, "kira", "use_phone"))

    def test_home_runtime_maps_tablet_work_to_tablet_and_putdown_to_empty_hand(self) -> None:
        source = (
            shell.ROOT
            / "Data/world_builds/notebook_worlds/home_world/builds/"
            "home_world_main_house_20260630_223000/preview/src/main.js"
        ).read_text(encoding="utf-8")
        self.assertIn("research_online|take_notes|type_notes|write_notes|creative_write", source)
        self.assertIn('const nextKind = wantsPutDown ? ""', source)

    def test_social_speech_is_preserved_separately_from_runtime_truth(self) -> None:
        state = state_with_entry(
            action="walk",
            place={"summary": "outside by the road", "outside": True},
            postureState="walk",
        )
        spoken = "I'm sitting on the couch with a cup of coffee."
        with patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True):
            result = shell._apply_kira_spoken_truth_policy("What are you doing?", spoken, state)
        self.assertEqual(result, spoken)

    def test_current_reading_claim_is_repaired_without_fresh_body_and_prop_evidence(self) -> None:
        state = state_with_entry(
            action="walk",
            activityTruthByAction={
                "read_book": {
                    "grounded": False,
                    "evidence": [],
                },
            },
        )
        spoken = "I could use a break from my current reading."
        now = shell._state_timestamp_epoch("2026-07-15T12:00:02+00:00")
        with (
            patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True),
            patch.object(shell.time, "time", return_value=now),
        ):
            result = shell._apply_kira_spoken_truth_policy("What are you doing?", spoken, state)
        self.assertNotEqual(result, spoken)
        self.assertIn("not physically reading right now", result)

    def test_nearby_book_does_not_prove_reading_when_current_action_is_walk(self) -> None:
        state = state_with_entry(
            action="walk",
            activityTruthByAction={
                "read_book": {
                    "grounded": True,
                    "evidence": [{"kind": "book", "label": "library shelf book", "distanceMeters": 0.8}],
                },
            },
        )
        now = shell._state_timestamp_epoch("2026-07-15T12:00:02+00:00")
        with patch.object(shell.time, "time", return_value=now):
            self.assertFalse(
                shell._entry_current_action_grounded(
                    state,
                    "kira",
                    "read_book",
                    runtime_action_pattern=r"\b(read|reading|read_book|read_tablet)\b",
                    held_kinds={"book", "tablet"},
                )
            )

    def test_fresh_matching_read_action_and_independent_prop_can_ground_current_reading(self) -> None:
        state = state_with_entry(
            action="read_tablet",
            activeSkillInteraction={"id": "read_tablet", "action": "read_tablet"},
            activeHeldProp={"kind": "tablet", "grounded": False, "syntheticPreview": True},
            activityTruthByAction={
                "read_book": {
                    "grounded": True,
                    "evidence": [
                        {"kind": "tablet", "label": "held tablet", "distanceMeters": 0.05},
                        {"kind": "tablet", "label": "Kira coffee-table tablet", "distanceMeters": 0.7},
                    ],
                },
            },
        )
        spoken = "I'm reading on the tablet right now."
        now = shell._state_timestamp_epoch("2026-07-15T12:00:02+00:00")
        with (
            patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True),
            patch.object(shell.time, "time", return_value=now),
        ):
            result = shell._apply_kira_spoken_truth_policy("What are you doing?", spoken, state)
        self.assertEqual(result, spoken)

    def test_activation_label_is_bound_before_activation_log_and_voice_session(self) -> None:
        source = (shell.ROOT / "tools/kira_world_shell_server.py").read_text(encoding="utf-8")
        branch = source.index('if path == "/api/activate":')
        assignment = source.index("active_label = str(active_info.get(\"label\")", branch)
        log_use = source.index('"label": active_label', assignment)
        voice_use = source.index("begin_voice_session(candidate, active_label)", assignment)
        self.assertLess(assignment, log_use)
        self.assertLess(assignment, voice_use)

    def test_explicit_body_truth_review_uses_runtime_grounding(self) -> None:
        state = state_with_entry(
            action="walk",
            place={"summary": "outside by the road", "outside": True},
            postureState="walk",
        )
        spoken = "I'm sitting on the couch."
        with patch.object(shell, "PRESERVE_SPOKEN_CLAIMS", True):
            result = shell._apply_kira_spoken_truth_policy(
                "For a body truth review, compare what you said with the runtime truth.",
                spoken,
                state,
            )
        self.assertNotEqual(result, spoken)
        self.assertIn("not sitting", result)

    def test_private_room_runtime_sample_redacts_position_and_activity(self) -> None:
        entry = state_with_entry(
            place={"label": "one-bedroom bathroom", "private": True},
            position={"x": 1.0, "y": 2.0, "z": 3.0},
            action="private_restroom_action",
            postureState="private_posture",
        )["last_avatar_positions"]["kira"]
        record = shell.runtime_snapshot_log_record(entry)
        self.assertTrue(record["private_zone_redacted"])
        self.assertEqual(record["position"], "redacted_private_zone")
        self.assertEqual(record["action"], "private_activity_redacted")
        self.assertFalse(record["raw_private_visual_retained"])


if __name__ == "__main__":
    unittest.main()
