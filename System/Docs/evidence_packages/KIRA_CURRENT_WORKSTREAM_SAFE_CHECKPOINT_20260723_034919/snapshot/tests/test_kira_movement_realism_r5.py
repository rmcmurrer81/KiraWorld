from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools" / "verify_kira_movement_realism_r5.mjs"
HOME_SOURCE = (
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


class KiraMovementRealismR5Tests(unittest.TestCase):
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
        cls.source = HOME_SOURCE.read_text(encoding="utf-8")

    def test_gradual_shortest_arc_turn_and_translation_pause(self) -> None:
        yaw = self.evidence["yaw"]
        self.assertTrue(self.evidence["pass"])
        self.assertLessEqual(yaw["largeTurn"]["maxFrameYawStep"], 2.65 / 60 + 1e-8)
        self.assertLessEqual(yaw["largeTurn"]["maxObservedAcceleration"], 6.4 + 1e-8)
        self.assertGreater(yaw["largeTurn"]["translationPausedFrames"], 10)
        self.assertLess(yaw["boundaryTurn"]["totalYawDistance"], 0.08)

    def test_collision_steering_and_recovery_never_cross_test_wall(self) -> None:
        collision = self.evidence["collision"]
        self.assertEqual(collision["sampledWallCrossings"], 0)
        self.assertEqual(collision["recoveryCollisionSamples"], 0)
        self.assertLessEqual(collision["recoveryMaxFrameStepMeters"], 0.3744 / 60 + 1e-8)
        self.assertIsNone(collision["fullyBlockedResult"])
        self.assertNotIn("activeMarker.position.lerpVectors(current, recovery", self.source)
        self.assertIn("axisWallSlideUsed: false", self.source)

    def test_ground_foot_and_relaxed_arm_bounds(self) -> None:
        ground = self.evidence["groundAndFeet"]
        arms = self.evidence["relaxedArms"]
        self.assertAlmostEqual(ground["finalBoundsGapMeters"], 0.0, places=6)
        self.assertGreaterEqual(ground["convergedCorrectionMeters"], ground["correctionBoundsMeters"][0])
        self.assertLessEqual(ground["convergedCorrectionMeters"], ground["correctionBoundsMeters"][1])
        self.assertTrue(ground["runtimeWorldPlantLockPresent"])
        self.assertTrue(arms["allSamplesWithinLimits"])
        self.assertGreater(arms["deterministicSamples"], 1000)
        self.assertFalse(arms["contactIkUsedForOrdinaryLocomotion"])
        self.assertGreaterEqual(arms["maximumGaitArmSwingRadians"], 0.3)

    def test_centered_home_entry_replan_reaches_person_chosen_destinations(self) -> None:
        entry = self.evidence["homeEntry"]
        self.assertTrue(entry["reproducedOldDiagonalWallCrossing"])
        self.assertTrue(entry["routeStartsAtCurrentBodyWithoutTeleport"])
        self.assertEqual(entry["centeredRouteWallCrossings"], 0)
        self.assertTrue(entry["outsideToInsideCrossing"])
        self.assertEqual(entry["destination"], "kitchen drink affordance")
        self.assertTrue(entry["laterCouchRoutePresent"])
        self.assertTrue(entry["stuckReplanRuntimePresent"])
        self.assertIn('routeId: "walk_inside_to_kitchen_drink"', self.source)
        self.assertIn('routeId: "walk_to_home_couch_sit"', self.source)

    def test_person_chosen_home_exit_uses_doorway_and_never_teleports(self) -> None:
        start = self.source.index("function startActiveAvatarHomeExitWalk")
        end = self.source.index("function startActiveAvatarHomeSitHold", start)
        exit_source = self.source[start:end]
        self.assertIn("planActiveAvatarOneBedroomInteriorRoute", exit_source)
        self.assertIn("oneBedroomHomeEntryCorridorWaypoints().reverse()", exit_source)
        self.assertIn('"door_opening_center"', exit_source)
        self.assertIn('"outside_door_threshold"', exit_source)
        self.assertIn('"front_walk_outside"', exit_source)
        self.assertNotIn("position.copy", exit_source)
        self.assertNotIn("position.set", exit_source)

    def test_idle_motion_is_nonzero_without_body_drift_or_forced_exam(self) -> None:
        idle = self.evidence["naturalIdle"]
        autonomy = self.evidence["autonomy"]
        self.assertGreater(idle["maximumIdleJointDeltaRadians"], 0.01)
        self.assertGreaterEqual(idle["movingRootBobMaxMeters"], 0.0059)
        self.assertGreater(idle["idleRootBobRangeMeters"], 0.001)
        self.assertEqual(idle["rootTranslationMeters"], {"x": 0, "y": 0, "z": 0})
        self.assertFalse(autonomy["liveDoctorHarnessMappingPresent"])
        self.assertEqual(autonomy["doctorOrMovementExamFromLiveAction"], "record_only_not_started")

    def test_body_snapshot_publishes_current_place_and_person_owned_route_progress(self) -> None:
        awareness = self.evidence["bodyAwareness"]
        self.assertTrue(awareness["currentWorldPositionPublished"])
        self.assertTrue(awareness["currentNamedPlacePublished"])
        self.assertTrue(awareness["personOwnedBodyIntentPublished"])
        self.assertTrue(awareness["routeStatusPublishedWhilePaused"])
        self.assertTrue(awareness["routeWaypointAndDistancePublished"])

    def test_runtime_evidence_remains_explicitly_unreviewed(self) -> None:
        self.assertFalse(self.evidence["visuallyReviewed"])
        self.assertIn("visuallyReviewedThisSession: false", self.source)

    def test_invalid_upstairs_runtime_state_never_teleports_to_spawn(self) -> None:
        continuity = self.evidence["continuity"]
        self.assertFalse(continuity["runtimeSpawnCopyPresent"])
        self.assertTrue(continuity["resumeValidationRejectsUpstairsKira"])
        self.assertEqual(
            continuity["invalidHeightBehavior"],
            "safe_stop_in_place_and_require_validated_reactivation_or_review",
        )
        movement = self.source[
            self.source.index("function updateActiveAvatarMovement") :
            self.source.index("function setStartPosition")
        ]
        self.assertNotIn("position.copy(KIRA_BUNGALOW_SPAWN)", movement)
        self.assertIn("invalid_height_safe_stop_no_runtime_teleport", movement)


if __name__ == "__main__":
    unittest.main()
