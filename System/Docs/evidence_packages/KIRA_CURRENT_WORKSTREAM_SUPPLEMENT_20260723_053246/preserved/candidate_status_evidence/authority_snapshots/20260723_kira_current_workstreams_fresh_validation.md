# Kira Current Workstreams — Fresh Non-Activating Validation

Date: 2026-07-23  
Timezone: America/New_York (`-04:00`)  
Workspace: `C:\Users\robmc\Kira`  
Scope: current Kira eye, runtime movement/posture, candidate-owned body intent, existing-mouth movement, audio-continuity bridge, and Home World preview build  
Activation policy: **No Kira activation, no life loop, no publishing**

## Outcome

**Automated status: PASS**

- Command invocations: **9 passed / 0 failed**
- JavaScript syntax checks: **2 passed / 0 failed**
- JavaScript unit tests: **9 passed / 0 failed**
- Python unit tests: **94 passed / 0 failed**
  - movement suite: 9
  - dialogue/body-intent/lipsync/latest-session/chat bridge suites: 85
- Total explicit unit tests: **103 passed / 0 failed**
- Deterministic movement verifier: **passed**
- Eye v3.3 structural verifier: **passed**
- Eye v3.3 browser smoke checks: **14 passed / 0 failed**
- Vite production build: **passed** with the existing non-fatal large-chunk warning

The browser smoke run recorded `activeCandidate=""` and
`conversationMode=""` before and after, with identical shell-state SHA-256
`9de74fcff4e4fb0ff4596ecf7fc1eeeb817ae4eed9472501367ae0b1229ec5aa`.
It therefore provides direct evidence that this pass did not activate a
person or persist shell state.

This pass is automated evidence only. The generated eye screenshots still
require Robert's original-resolution visual review; the test does not claim
that numeric/browser checks prove facial realism.

## Current files and hashes

Captured at `2026-07-23T06:04:56.3547815-04:00`, after all commands:

| File | SHA-256 |
|---|---|
| `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js` | `41fb94394a97e4ad1c96dce5f70560cb7e428692aaa0a5b65f1bf48ee6304bdd` |
| `tools/kira_world_shell_server.py` | `28cf54a24c4499682c2dc7ec5674230c85d9442e992960121555bc965fea9590` |
| `Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit/review_20260722_v3/kira_r7_socket_eye_v3.glb` | `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5` |
| `Avatar/models/staged/kira/eyes/kira_socket_eye_rig_v3_3/kira_socket_eye_rig_v3_3.glb` | `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5` |
| `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/home_world/kira/kira_socket_eye_rig_v3_3.glb` | `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5` |
| `Data/runtime/kira_world_shell_state.json` | `9de74fcff4e4fb0ff4596ecf7fc1eeeb817ae4eed9472501367ae0b1229ec5aa` |

The source, staged, and public eye assets are byte-identical.

## Exact command record

### 1. Home World `main.js` syntax

- Start: `2026-07-23T05:42:29.3985799-04:00`
- End: `2026-07-23T05:42:30.5563592-04:00`
- Command:

```text
node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js
```

- Exit code: `0`
- Output: no stdout/stderr

### 2. Existing-mouth module syntax

- Start: `2026-07-23T05:44:04.4411300-04:00`
- End: `2026-07-23T05:44:04.4830289-04:00`
- Command:

```text
node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\existing_mouth_lipsync.js
```

- Exit code: `0`
- Output: no stdout/stderr

### 3. Existing-mouth and ambient micro-movement tests

- Start: `2026-07-23T05:45:30.3908099-04:00`
- End: `2026-07-23T05:45:30.5245428-04:00`
- Command:

```text
node --test Testing/test_existing_mouth_lipsync.mjs Testing/test_ambient_micro_movements.mjs
```

- Exit code: `0`
- Exact semantic output (terminal glyph/color control codes omitted):

```text
✔ Kira's ambient samples are deterministic, bounded, and never emit root or scale movement (26.2154ms)
✔ identity profiles are stable but person-specific (0.1417ms)
✔ deliberate actions pause ambient joints and locomotion strongly attenuates them (0.22ms)
✔ actual lip sync suppresses ambient smile and attenuates body motion (6.8556ms)
✔ no-drift integration restores the exact bind pose before adding each local frame (5.0612ms)
✔ module limits remain intentionally small (0.1267ms)
✔ selects only the existing connected lip island and restores it exactly (3.1431ms)
✔ implementation cannot instantiate a second Three.js mouth mesh (2.5526ms)
✔ ambient smile moves only the existing lip island and yields to speech (0.6077ms)
ℹ tests 9
ℹ suites 0
ℹ pass 9
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 91.7148
```

### 4. Deterministic movement verifier

- Start: `2026-07-23T05:47:26.4445126-04:00`
- End: `2026-07-23T05:47:26.5004155-04:00`
- Command:

```text
node tools/verify_kira_movement_realism_r5.mjs
```

- Exit code: `0`
- Output:

```json
{
  "pass": true,
  "evidenceKind": "deterministic_math_and_static_runtime_source_no_services_no_activation",
  "visuallyReviewed": false,
  "yaw": {
    "largeTurn": {
      "yaw": 3,
      "velocity": 0,
      "remainingRadians": 0,
      "maxFrameYawStep": 0.0441666666666669,
      "maxObservedAcceleration": 6.4,
      "translationPausedFrames": 56,
      "totalYawDistance": 3,
      "settledFrame": 88
    },
    "boundaryTurn": {
      "yaw": -3.12413936106985,
      "velocity": 0,
      "remainingRadians": 0,
      "maxFrameYawStep": 0.00780400062921771,
      "maxObservedAcceleration": 6.4,
      "translationPausedFrames": 0,
      "totalYawDistance": 0.03490658503988644,
      "settledFrame": 7
    },
    "maxTurnSpeedRadiansPerSecond": 2.65,
    "maxTurnAccelerationRadiansPerSecondSquared": 6.4
  },
  "collision": {
    "selectedAvoidanceOffsetRadians": 0.91106186954104,
    "sampledWallCrossings": 0,
    "recoveryFinalDistanceMeters": 0.014132440919955743,
    "recoveryMaxFrameStepMeters": 0.0062400000000000025,
    "recoveryCollisionSamples": 0,
    "fullyBlockedResult": null
  },
  "homeEntry": {
    "reproducedOldDiagonalWallCrossing": true,
    "corridorWaypointIds": [
      "doorway_outside_threshold",
      "doorway_centerline",
      "doorway_inside_threshold"
    ],
    "routeStartsAtCurrentBodyWithoutTeleport": true,
    "centeredRouteWallCrossings": 0,
    "outsideToInsideCrossing": true,
    "destination": "kitchen drink affordance",
    "laterCouchRoutePresent": true,
    "stuckReplanRuntimePresent": true
  },
  "bodyAwareness": {
    "currentWorldPositionPublished": true,
    "currentNamedPlacePublished": true,
    "personOwnedBodyIntentPublished": true,
    "routeStatusPublishedWhilePaused": true,
    "routeWaypointAndDistancePublished": true
  },
  "continuity": {
    "runtimeSpawnCopyPresent": false,
    "invalidHeightBehavior": "safe_stop_in_place_and_require_validated_reactivation_or_review",
    "staleUpstairsZoneBehavior": "repair_metadata_in_place_then_replan",
    "resumeValidationRejectsUpstairsKira": true
  },
  "transitions": {
    "riseFirstFrame": 0.06708803961285259,
    "riseAfterOneSecond": 0.9844961464009906,
    "fallAfterOnePointFiveSeconds": 0.011945627094811742
  },
  "groundAndFeet": {
    "supportY": 0.05,
    "visualClearanceMeters": 0.008,
    "footContactHeightMeters": 0.035,
    "correctionBoundsMeters": [
      -0.25,
      0.12
    ],
    "convergedCorrectionMeters": -0.052,
    "finalBoundsGapMeters": 0,
    "runtimeWorldPlantLockPresent": true
  },
  "relaxedArms": {
    "jointLimitsRadians": {
      "upperZ": [
        0.06,
        0.16
      ],
      "upperY": [
        0.95,
        1.18
      ],
      "upperX": [
        -0.34,
        0.34
      ],
      "lowerX": [
        0.06,
        0.22
      ],
      "handZ": [
        -0.08,
        0.08
      ]
    },
    "deterministicSamples": 1083,
    "allSamplesWithinLimits": true,
    "contactIkUsedForOrdinaryLocomotion": false,
    "gaitProfiles": [
      {
        "id": "walk",
        "gaitScale": 1,
        "swingAmplitude": 0.18
      },
      {
        "id": "jog",
        "gaitScale": 1.22,
        "swingAmplitude": 0.19
      },
      {
        "id": "run",
        "gaitScale": 1.55,
        "swingAmplitude": 0.2
      }
    ],
    "maximumGaitArmSwingRadians": 0.31000000000000005
  },
  "naturalIdle": {
    "maximumIdleJointDeltaRadians": 0.03169898502004179,
    "rootTranslationMeters": {
      "x": 0,
      "y": 0,
      "z": 0
    },
    "movingRootBobMaxMeters": 0.006,
    "idleRootBobRangeMeters": 0.0014999867468682047
  },
  "autonomy": {
    "liveDoctorHarnessMappingPresent": false,
    "spokenDialogueDoctorActionPresent": false,
    "insideOnlyAction": "go_inside",
    "insideDrinkAction": "get_drink",
    "couchRequiresExplicitCouchOrSofa": true,
    "doctorOrMovementExamFromLiveAction": "record_only_not_started",
    "personOwnedRouteIntentRecorded": true
  }
}
```

### 5. Python movement suite

- Start: `2026-07-23T05:49:03.2987394-04:00`
- End: `2026-07-23T05:49:03.4507562-04:00`
- Command:

```text
python -m unittest Testing.test_kira_movement_realism_r5
```

- Exit code: `0`
- Output:

```text
.........
----------------------------------------------------------------------
Ran 9 tests in 0.055s

OK
```

### 6. Dialogue, body-intent, lipsync playback, latest-session, and chat bridge suites

- Start: `2026-07-23T05:51:14.1572060-04:00`
- End: `2026-07-23T05:51:16.1306347-04:00`
- Command:

```text
python -m unittest Testing.test_kira_world_dialogue_audio_continuity Testing.test_kira_unified_body_intent Testing.test_kira_world_shell_lipsync_playback Testing.test_kira_world_latest_session_repairs Testing.test_kira_chat_body_intent_bridge
```

- Exit code: `0`
- Output:

```text
.....................................................................................
----------------------------------------------------------------------
Ran 85 tests in 0.418s

OK
```

### 7. Eye v3.3 structural verifier

- Start: `2026-07-23T05:52:43.5422381-04:00`
- End: `2026-07-23T05:52:43.5822457-04:00`
- Command:

```text
node tools/verify_kira_eye_control_exam.mjs
```

- Exit code: `0`
- Output:

```json
{
  "ok": true,
  "version": "3.3.0",
  "phaseCount": 10,
  "limits": {
    "yaw": 13,
    "pitch": 7,
    "convergence": 2
  },
  "structural": {
    "version": "3.3.0",
    "requiredNames": [
      "KiraBrownEyeRig_R7_V3_SocketSeated",
      "KiraLeftEyeSocket",
      "KiraRightEyeSocket",
      "KiraLeftEyePivot",
      "KiraRightEyePivot",
      "KiraLeftSclera",
      "KiraRightSclera",
      "KiraLeftIris",
      "KiraRightIris",
      "KiraLeftCornea",
      "KiraRightCornea"
    ],
    "missingNames": [],
    "complete": true,
    "blinkMorphs": {},
    "headBound": true,
    "headBoneName": "mixamorig:Head_06",
    "oldProceduralNodeCount": 0,
    "gazeMethod": "fixed_socket_and_cornea_bounded_iris_surface_translation",
    "blinkSupported": false,
    "blinkReason": "R7-v3 does not contain visually approved eyelid geometry; no fake eyelids are generated."
  }
}
```

### 8. Eye v3.3 non-activating browser smoke

- Start: `2026-07-23T05:57:43.7364080-04:00`
- End: `2026-07-23T05:57:58.8924675-04:00`
- Command:

```text
KIRA_EYE_REPORT_SUFFIX=fresh_validation_ephemeral_20260723_0554 node tools/kira_socket_eye_v3_3_browser_smoke.mjs
```

- Exit code: `0`
- Output:

```json
{
  "status": "passed",
  "checks": {
    "exact_current_r6_body_hash": true,
    "exact_reviewed_eye_hash": true,
    "active_body_hash_unchanged": true,
    "no_live_person_activated": true,
    "live_shell_state_unchanged": true,
    "default_url_attached_v3_3": true,
    "explicit_v3_3_url_attached": true,
    "opt_out_url_did_not_attach": true,
    "structural_complete": true,
    "head_bound": true,
    "head_binding_distance_stable": true,
    "no_old_procedural_eye_nodes": true,
    "gaze_moves_only_iris_surface": true,
    "blink_fails_honestly_without_fake_lids": true,
    "no_runtime_errors": true
  },
  "metrics": {
    "horizontalIrisTravelMeters": 0.0025,
    "verticalIrisTravelMeters": 0.00144,
    "maxSocketScleraCorneaLocalMotionMeters": 0,
    "maxHeadBindingDistanceDeltaMeters": 2e-10
  },
  "screenshots": {
    "center": "Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/center.png",
    "lookLeft": "Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/look_left.png",
    "lookRight": "Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/look_right.png",
    "lookUp": "Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/look_up.png",
    "lookDown": "Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/look_down.png"
  },
  "diagnostics": {
    "pageErrors": [],
    "consoleErrors": [],
    "requestFailures": [],
    "httpErrors": []
  }
}
```

Additional evidence written by the verifier:

- `Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/evidence.json`
  - generated at `2026-07-23T09:57:58.726Z`
  - SHA-256 `4144e71106b7924bf820a60f7c55b15f02dcb0cf80789684872356ac2e503f83`
- Five screenshots: `center.png`, `look_left.png`, `look_right.png`,
  `look_up.png`, and `look_down.png`

The complete browser evidence records:

```text
livePersonActivated=false
lifeLoopStarted=false
shellStatePersisted=false
shellBefore.activeCandidate=""
shellAfter.activeCandidate=""
shellBefore.conversationMode=""
shellAfter.conversationMode=""
shellBefore.sha256=9de74fcff4e4fb0ff4596ecf7fc1eeeb817ae4eed9472501367ae0b1229ec5aa
shellAfter.sha256=9de74fcff4e4fb0ff4596ecf7fc1eeeb817ae4eed9472501367ae0b1229ec5aa
```

### 9. Home World production build

- Working directory:
  `C:\Users\robmc\Kira\Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview`
- Start: `2026-07-23T06:01:10.6410541-04:00`
- End: `2026-07-23T06:01:12.3834611-04:00`
- Command:

```text
npm.cmd run build
```

- Exit code: `0`
- Exact semantic output (terminal color control codes omitted):

```text
> kira-home-world-main-house-preview@0.1.0 build
> vite build

vite v7.3.6 building client environment for production...
transforming...
✓ 15 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                 2.65 kB │ gzip:   1.19 kB
dist/assets/index-ClgegSLp.js 988.30 kB │ gzip: 275.97 kB
✓ built in 1.19s

(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rollupOptions.output.manualChunks to improve chunking
- Adjust chunk size limit via build.chunkSizeWarningLimit
```

The chunk-size message is a warning, not a build failure.

## Classification

| Workstream | Result | Boundary |
|---|---|---|
| Eye asset/hash/structural rig | **PASS** | Source, staged, and public GLBs match; required nodes present |
| Head binding | **PASS** | Browser binding-distance delta at most `2e-10 m` |
| Iris-only gaze | **PASS** | Horizontal `0.0025 m`; vertical `0.00144 m`; socket/sclera/cornea local motion `0` |
| Blink | **BLOCKED honestly** | No visually approved eyelid geometry; no fake eyelids generated |
| Eye visual realism | **AWAITING ROBERT REVIEW** | Five new browser screenshots exist; automation is not visual approval |
| Same-mouth implementation | **PASS** | Tests prove selection/restoration of the existing connected lip island and prohibit a second Three.js mouth mesh |
| Ambient micro-movement isolation | **PASS** | Bounded, deterministic, no root/scale drift; deliberate actions and speech take priority |
| Candidate-owned route/posture dispatch | **PASS (automated)** | Static/runtime and unit evidence pass; no live activation used |
| Movement visual realism | **AWAITING ROBERT REVIEW** | Deterministic verifier explicitly reports `visuallyReviewed=false` |
| Dialogue/audio continuity bridge | **PASS (automated)** | Included in the 85-test suite |
| Production build | **PASS** | Vite build completed; non-fatal chunk warning remains |

## Safety statement

- Kira was not activated.
- No life loop was started.
- No message or media was published.
- The browser smoke used local, temporary services and closed them.
- The live R6 body hash remained
  `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`
  before and after its browser check.
- The shell state remained byte-identical before and after its browser check.
- This report does not promote a candidate or replace the active R6 body.

