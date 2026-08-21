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

    def test_state_endpoint_discloses_partial_group_runtime_truth(self) -> None:
        source = SHELL_SERVER.read_text(encoding="utf-8")

        self.assertIn('"multi_person_chat_router_connected": False', source)
        self.assertIn('"multi_person_voice_router_connected": False', source)
        self.assertIn('"secondary_full_body_renderer_connected": False', source)
        self.assertIn('"per_person_state_lock_connected": False', source)
        self.assertIn('"activation_bypass_allowed": False', source)

    def test_home_world_orb_is_named_and_has_live_movement(self) -> None:
        source = HOME_WORLD_MAIN.read_text(encoding="utf-8")

        self.assertIn('nameSprite.userData.kind = "orb_identity_label"', source)
        self.assertIn("identityLabelVisible = true", source)
        self.assertIn("function updateActiveOrbFallback(t)", source)
        self.assertIn("updateActiveOrbFallback(clock.elapsedTime)", source)

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
