from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools" / "verify_kira_doctor_body_control_exam.mjs"
SOURCE = (
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


class KiraDoctorBodyControlExamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        completed = subprocess.run(
            ["node", str(VERIFY)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        cls.evidence = json.loads(completed.stdout)
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_exact_current_skin_has_every_named_exam_joint(self) -> None:
        self.assertTrue(self.evidence["pass"])
        rig = self.evidence["rig"]
        exam = self.evidence["exam"]
        self.assertEqual(exam["jointPhases"], 32)
        self.assertEqual(exam["structurallySupported"], 32)
        self.assertEqual(exam["executedByThisOfflineCheck"], 0)
        self.assertEqual(exam["falselyPromotedToPass"], 0)
        self.assertEqual(rig["animationClipCount"], 0)
        for side in ("L", "R"):
            for count in rig["fingerPhalangesPerFinger"][side].values():
                self.assertEqual(count, 4)

    def test_negative_control_and_eye_limit_are_honest(self) -> None:
        exam = self.evidence["exam"]
        self.assertEqual(exam["negativeControl"]["status"], "fail_missing_joint")
        self.assertFalse(exam["negativeControl"]["passed"])
        self.assertEqual(exam["eyeMovement"]["status"], "not_tested_separate_eye_rig")
        self.assertFalse(exam["eyeMovement"]["passed"])

    def test_comfort_idle_moves_joints_but_never_requests_translation(self) -> None:
        idle = self.evidence["comfortIdle"]
        self.assertEqual(idle["rootTranslationRequested"], {"x": 0, "y": 0, "z": 0})
        self.assertGreater(idle["maxIdleHipsRadians"], 0.02)
        self.assertGreater(idle["maxIdleHeadYawRadians"], 0.06)
        self.assertGreater(idle["maxTalkingShoulderRadians"], idle["maxIdleShoulderRadians"])
        self.assertGreater(idle["individualFingerPulseRange"], 1.5)

    def test_current_ground_lie_has_clearance_gate_and_no_position_rewrite(self) -> None:
        ground = self.evidence["groundLie"]
        self.assertEqual(ground["samplesRequiredAtRuntime"], 15)
        self.assertFalse(ground["directPositionRewritePresent"])
        self.assertIn("clear_supported_body_length_floor_area_required", self.source)
        self.assertIn("positionChangedForPosture: false", self.source)

    def test_person_owned_shell_action_can_start_exam(self) -> None:
        self.assertIn("doctor_body_control_exam", self.source)
        self.assertIn("mindOrLifeLoopActivatedByProbe: false", self.source)
        self.assertNotIn("livePersonActivated: false", self.source)

    def test_server_body_intents_route_to_bounded_execution(self) -> None:
        shell_bridge = self.source[
            self.source.index("function maybeStartBodyPracticeFromShellAction") :
            self.source.index("function activeAvatarDefaultRoamZone")
        ]
        self.assertIn('normalized === "raise_hand"', shell_bridge)
        self.assertIn('/^(walk|jog|run)$/.test(normalized)', shell_bridge)
        self.assertIn("sit_on_couch|couch|sofa", shell_bridge)
        self.assertIn("lie_on_couch", shell_bridge)
        self.assertIn("lie_on_bed", shell_bridge)
        self.assertIn("go_library", shell_bridge)
        self.assertIn("selfChosen: true", shell_bridge)


if __name__ == "__main__":
    unittest.main()
