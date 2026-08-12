from __future__ import annotations

import unittest
from pathlib import Path

from tools import kira_world_shell_server as shell


ROOT = Path(__file__).resolve().parents[1]
HOME_SOURCE = (
    ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds/"
    "home_world_main_house_20260630_223000/preview/src/main.js"
)


class AvatarResumeWardrobePersistenceTests(unittest.TestCase):
    def test_resume_position_keeps_only_valid_executable_wardrobe_state(self) -> None:
        entry = {
            "candidate": "kira",
            "location": "home",
            "position": {"x": -1.2, "y": 0.05, "z": 26.2},
            "wardrobeState": {
                "schemaVersion": 99,
                "garments": [
                    {
                        "id": "dress_shirt_001",
                        "label": "prototype dress shirt",
                        "state": "WornClosed",
                        "lifecycle": "WORN_CLOSED",
                        "buttoned": True,
                        "selected": True,
                        "history": [{"arbitrary": "renderer history is not persisted"}],
                    },
                    {"id": "bad", "state": "TeleportOntoBody"},
                ],
            },
            "rotationY": 1.125,
        }

        saved = shell._valid_resume_position(entry)

        self.assertIsNotNone(saved)
        wardrobe = saved["wardrobeState"]
        self.assertEqual(wardrobe["schemaVersion"], 1)
        self.assertEqual(wardrobe["equippedGarmentIds"], ["dress_shirt_001"])
        self.assertEqual(len(wardrobe["garments"]), 1)
        self.assertTrue(wardrobe["garments"][0]["buttoned"])
        self.assertNotIn("history", wardrobe["garments"][0])
        self.assertEqual(saved["rotationY"], 1.125)

    def test_invalid_wardrobe_does_not_invalidate_safe_resume_position(self) -> None:
        saved = shell._valid_resume_position(
            {
                "candidate": "kira",
                "location": "home",
                "position": {"x": 1, "y": 0.05, "z": 2},
                "wardrobeState": {"garments": [{"id": "shirt", "state": "Invalid"}]},
            }
        )
        self.assertIsNotNone(saved)
        self.assertNotIn("wardrobeState", saved)

    def test_home_runtime_snapshots_and_restores_same_visible_garment_state(self) -> None:
        source = HOME_SOURCE.read_text(encoding="utf-8")
        self.assertIn("function activeAvatarWardrobeSnapshot()", source)
        self.assertIn("function applyActiveAvatarWardrobeResumeState(wardrobeState)", source)
        self.assertIn("wardrobeState: activeAvatarWardrobeSnapshot()", source)
        self.assertIn("applyActiveAvatarWardrobeResumeState(resume.wardrobeState)", source)
        self.assertIn("restore_same_visible_garment_state_without_replaying_dressing_animation", source)
        self.assertIn("rotationY: Number(activeMarker.rotation.y.toFixed(6))", source)

    def test_shell_waits_for_snapshot_ack_before_deactivation(self) -> None:
        source = (ROOT / "tools/kira_world_shell_server.py").read_text(encoding="utf-8")
        self.assertIn("async function persistAvatarSnapshotBeforeStateChange", source)
        self.assertIn("lastAvatarSnapshotAckAt >= requestedAt", source)
        self.assertIn("const snapshotSaved = await persistAvatarSnapshotBeforeStateChange();", source)


if __name__ == "__main__":
    unittest.main()
