from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL_SERVER = ROOT / "tools" / "kira_world_shell_server.py"
HOME_WORLD_MAIN = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "home_world"
    / "builds"
    / "home_world_main_house_20260630_223000"
    / "preview"
    / "src"
    / "main.js"
)


class WorldShellGroupSessionContractTests(unittest.TestCase):
    def test_shell_exposes_revisioned_per_person_session_state(self) -> None:
        source = SHELL_SERVER.read_text(encoding="utf-8")

        self.assertIn('"active_sessions": {}', source)
        self.assertIn('"active_sessions_revision": 0', source)
        self.assertIn("def candidate_state_lock(candidate_id: str)", source)
        self.assertIn('"state_namespace": candidate', source)
        self.assertIn('"write_serialization": "per_candidate_lock_plus_shell_state_revision"', source)

    def test_state_endpoint_discloses_connected_group_runtime_truth(self) -> None:
        source = SHELL_SERVER.read_text(encoding="utf-8")

        self.assertIn('"multi_person_chat_router_connected": True', source)
        self.assertIn('"multi_person_voice_router_connected": True', source)
        self.assertIn('"secondary_full_body_renderer_connected": False', source)
        self.assertIn('"secondary_named_orb_renderer_connected": True', source)
        self.assertIn('"per_person_state_lock_connected": True', source)
        self.assertIn('"secondary_sensory_initiative_ownership": False', source)
        self.assertIn('"activation_bypass_allowed": False', source)

    def test_activation_requires_explicit_group_join_and_checks_capacity(self) -> None:
        source = SHELL_SERVER.read_text(encoding="utf-8")

        self.assertIn('join_group = body.get("join_group") is True', source)
        self.assertIn("def active_session_activation_plan(", source)
        self.assertIn('"active_session_capacity_reached"', source)
        self.assertIn('"sensory_lease_started": False', source)
        self.assertIn('"initiative_transport_started": False', source)
        self.assertIn('"voice_session_started": False', source)

    def test_group_chat_is_sequential_and_uses_per_person_locks(self) -> None:
        source = SHELL_SERVER.read_text(encoding="utf-8")

        self.assertIn('if path == "/api/group-chat":', source)
        self.assertIn("run_sequential_group_turn(", source)
        self.assertIn("lock_for=candidate_state_lock", source)
        self.assertIn('"parallel_reply_generation": False', source)
        self.assertIn('"parallel_voice_playback": False', source)
        self.assertIn('"single_fifo_output_worker"', source)
        self.assertIn("wait_for_completion=True", source)
        self.assertIn('"playback_serialized_and_awaited": True', source)

    def test_home_world_orb_is_named_and_has_live_movement(self) -> None:
        source = HOME_WORLD_MAIN.read_text(encoding="utf-8")

        self.assertIn('nameSprite.userData.kind = "orb_identity_label"', source)
        self.assertIn("identityLabelVisible = true", source)
        self.assertIn("function updateActiveOrbFallback(t)", source)
        self.assertIn("updateActiveOrbFallback(clock.elapsedTime)", source)
        self.assertIn("const groupPresenceOrbs = new Map()", source)
        self.assertIn("function syncGroupPresenceOrbs(shellState)", source)
        self.assertIn("function updateGroupPresenceOrbs(t)", source)
        self.assertIn("updateGroupPresenceOrbs(clock.elapsedTime)", source)
        self.assertIn('marker.userData.sensoryInitiativeOwner = false', source)
        self.assertIn('activeMarker.userData.kind = "body_load_blocked_named_orb_presence"', source)
        self.assertIn("activeMarker.add(makeOrbMarker(label))", source)

    def test_invalid_or_missing_body_uses_orb_without_body_substitution(self) -> None:
        source = SHELL_SERVER.read_text(encoding="utf-8")

        self.assertIn("named moving orb fallback only", source)
        self.assertIn(
            '"eligible_when_downloaded_person_has_no_usable_body": True', source
        )
        self.assertIn('"body_or_person_identity_substitution_allowed": False', source)
        self.assertNotIn("no substitute body or orb is rendered", source)


if __name__ == "__main__":
    unittest.main()
