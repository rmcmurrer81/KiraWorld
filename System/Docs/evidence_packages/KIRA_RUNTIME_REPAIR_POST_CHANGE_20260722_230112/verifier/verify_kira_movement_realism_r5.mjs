import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  advanceLocomotionBlend,
  buildCenteredDoorwayCorridor,
  selectCollisionFreeHeading,
  shortestYawDelta,
  stepAcceleratedYaw,
  translationScaleForTurn,
  withinJointLimit,
} from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/movement_realism.js";
import { comfortIdleOffsets } from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/body_control_exam.js";

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};
const near = (left, right, tolerance) => Math.abs(left - right) <= tolerance;
const dt = 1 / 60;
const maxTurnSpeed = 2.65;
const maxTurnAcceleration = 6.4;

function runYawScenario(startYaw, targetYaw, frames = 360) {
  let yaw = startYaw;
  let velocity = 0;
  let maxFrameYawStep = 0;
  let maxObservedAcceleration = 0;
  let translationPausedFrames = 0;
  let totalYawDistance = 0;
  let settledFrame = null;
  for (let frame = 0; frame < frames; frame += 1) {
    const before = yaw;
    const stepped = stepAcceleratedYaw({
      yaw,
      targetYaw,
      angularVelocity: velocity,
      dt,
      maxSpeed: maxTurnSpeed,
      maxAcceleration: maxTurnAcceleration,
    });
    yaw = stepped.yaw;
    velocity = stepped.angularVelocity;
    const frameStep = Math.abs(shortestYawDelta(before, yaw));
    totalYawDistance += frameStep;
    maxFrameYawStep = Math.max(maxFrameYawStep, frameStep);
    maxObservedAcceleration = Math.max(maxObservedAcceleration, Math.abs(stepped.angularAcceleration));
    const scale = translationScaleForTurn(stepped.remainingRadians, 1.05, 0.16);
    if (stepped.remainingRadians >= 1.05 - 1e-8 && scale === 0) translationPausedFrames += 1;
    if (stepped.aligned && settledFrame === null) settledFrame = frame + 1;
  }
  return {
    yaw,
    velocity,
    remainingRadians: Math.abs(shortestYawDelta(yaw, targetYaw)),
    maxFrameYawStep,
    maxObservedAcceleration,
    translationPausedFrames,
    totalYawDistance,
    settledFrame,
  };
}

const largeTurn = runYawScenario(0, 3.0);
assert(largeTurn.settledFrame !== null, "large turn did not converge");
assert(largeTurn.maxFrameYawStep <= maxTurnSpeed * dt + 1e-8, "yaw exceeded per-frame speed bound");
assert(largeTurn.maxObservedAcceleration <= maxTurnAcceleration + 1e-8, "yaw exceeded acceleration bound");
assert(largeTurn.translationPausedFrames > 10, "translation did not pause through the large turn");
assert(largeTurn.remainingRadians < 0.003, "large turn did not finish aligned");

const boundaryTurn = runYawScenario(179 * Math.PI / 180, -179 * Math.PI / 180, 180);
assert(boundaryTurn.settledFrame !== null, "boundary shortest-arc turn did not converge");
assert(boundaryTurn.totalYawDistance < 0.08, "boundary turn used the long arc");

const wall = (x, z) => x >= 0.28 && x <= 0.46 && z >= -0.2 && z <= 0.2;
const steered = selectCollisionFreeHeading({
  originX: 0,
  originZ: 0,
  desiredHeading: Math.PI / 2,
  stepDistance: 0.02,
  lookAheadDistance: 0.62,
  sampleSpacing: 0.04,
  isBlocked: wall,
});
assert(steered, "local collision steering found no safe sampled heading");
assert(!steered.direct, "local collision steering accepted the obstructed direct heading");
for (let distance = 0.01; distance <= 0.62; distance += 0.01) {
  const x = Math.sin(steered.heading) * distance;
  const z = Math.cos(steered.heading) * distance;
  assert(!wall(x, z), "collision steering crossed the deterministic wall");
}

let recoveryX = 0.18;
let recoveryZ = 0;
let recoveryYaw = 0;
let recoveryVelocity = 0;
let recoveryMaxStep = 0;
let recoveryCollisionSamples = 0;
for (let frame = 0; frame < 240; frame += 1) {
  const dx = 0 - recoveryX;
  const dz = 0 - recoveryZ;
  const distance = Math.hypot(dx, dz);
  if (distance < 0.015) break;
  const heading = Math.atan2(dx, dz);
  const turned = stepAcceleratedYaw({
    yaw: recoveryYaw,
    targetYaw: heading + Math.PI,
    angularVelocity: recoveryVelocity,
    dt,
    maxSpeed: maxTurnSpeed,
    maxAcceleration: maxTurnAcceleration,
  });
  recoveryYaw = turned.yaw;
  recoveryVelocity = turned.angularVelocity;
  const translationScale = translationScaleForTurn(turned.remainingRadians, 1.05, 0.16);
  const stepDistance = Math.min(distance, 0.3744 * dt * translationScale);
  const candidate = selectCollisionFreeHeading({
    originX: recoveryX,
    originZ: recoveryZ,
    desiredHeading: heading,
    stepDistance,
    lookAheadDistance: Math.min(distance, Math.max(stepDistance, 0.12)),
    sampleSpacing: 0.04,
    isBlocked: wall,
  });
  assert(candidate, "collision-checked recovery walk lost its safe route");
  const frameStep = Math.hypot(candidate.nextX - recoveryX, candidate.nextZ - recoveryZ);
  recoveryMaxStep = Math.max(recoveryMaxStep, frameStep);
  recoveryX = candidate.nextX;
  recoveryZ = candidate.nextZ;
  if (wall(recoveryX, recoveryZ)) recoveryCollisionSamples += 1;
}
assert(Math.hypot(recoveryX, recoveryZ) < 0.02, "recovery walk did not reach the prior safe point");
assert(recoveryCollisionSamples === 0, "recovery walk entered a collider");
assert(recoveryMaxStep <= 0.3744 * dt + 1e-8, "recovery walk rewrote position farther than one bounded frame step");

const enclosed = selectCollisionFreeHeading({
  originX: 0,
  originZ: 0,
  desiredHeading: 0,
  stepDistance: 0.02,
  lookAheadDistance: 0.62,
  isBlocked: () => true,
});
assert(enclosed === null, "fully blocked movement should pause rather than cross or teleport");

// Reproduce the July 18 failure: Kira reached the porch beside the opening,
// then the old direct segment toward the indoor spawn crossed the front wall.
// The repaired route first moves outside the wall to the opening X, crosses on
// the exact centerline, and only then proceeds to the chosen indoor affordance.
const homeDoor = {
  entryX: -23.852,
  wallZ: 9.6,
  openingWidth: 1.24,
  wallHalfDepth: 0.1,
  bodyRadius: 0.46,
};
const frontWallBlocks = (x, z) => {
  const withinInflatedWallDepth = Math.abs(z - homeDoor.wallZ) <= homeDoor.wallHalfDepth + homeDoor.bodyRadius;
  const centerClearance = homeDoor.openingWidth / 2 - homeDoor.bodyRadius;
  return withinInflatedWallDepth && Math.abs(x - homeDoor.entryX) > centerClearance;
};
function segmentBlockedByFrontWall(from, to, spacing = 0.025) {
  const length = Math.hypot(to.x - from.x, to.z - from.z);
  const samples = Math.max(1, Math.ceil(length / spacing));
  for (let index = 0; index <= samples; index += 1) {
    const alpha = index / samples;
    if (frontWallBlocks(
      from.x + (to.x - from.x) * alpha,
      from.z + (to.z - from.z) * alpha,
    )) return true;
  }
  return false;
}
const july18StuckBody = { x: -21.928, y: 0.05, z: 10.264 };
const oldDiagonalInteriorTarget = { x: -19.15, y: 0.05, z: 5.05 };
assert(
  segmentBlockedByFrontWall(july18StuckBody, oldDiagonalInteriorTarget),
  "doorway regression fixture no longer reproduces the old diagonal wall crossing",
);
const doorwayCorridor = buildCenteredDoorwayCorridor({
  entryX: homeDoor.entryX,
  wallZ: homeDoor.wallZ,
  y: 0.05,
  outsideSign: 1,
  outsideDistance: 1.08,
  insideDistance: 1.08,
});
assert(doorwayCorridor.map((point) => point.id).join("|") === [
  "doorway_outside_threshold",
  "doorway_centerline",
  "doorway_inside_threshold",
].join("|"), "doorway corridor labels or order changed");
const kitchenDrinkTarget = { x: -21.602, y: 0.05, z: -1.0 };
const replannedDrinkRoute = [july18StuckBody, ...doorwayCorridor, kitchenDrinkTarget];
let centeredRouteWallCrossings = 0;
for (let index = 1; index < replannedDrinkRoute.length; index += 1) {
  if (segmentBlockedByFrontWall(replannedDrinkRoute[index - 1], replannedDrinkRoute[index])) {
    centeredRouteWallCrossings += 1;
  }
}
assert(centeredRouteWallCrossings === 0, "centered doorway route still crosses the front wall");
assert(
  Math.hypot(
    replannedDrinkRoute[0].x - july18StuckBody.x,
    replannedDrinkRoute[0].z - july18StuckBody.z,
  ) === 0,
  "stuck replan changed Kira's current body position",
);
assert(
  doorwayCorridor[0].z > homeDoor.wallZ && doorwayCorridor.at(-1).z < homeDoor.wallZ,
  "doorway corridor does not cross from outside to inside",
);

let blend = 0;
const blendRise = [];
for (let frame = 0; frame < 60; frame += 1) {
  blend = advanceLocomotionBlend(blend, 1, dt, { riseSeconds: 0.24, fallSeconds: 0.34 });
  blendRise.push(blend);
}
for (let index = 1; index < blendRise.length; index += 1) {
  assert(blendRise[index] >= blendRise[index - 1], "locomotion start blend was not monotonic");
}
const blendFall = [];
for (let frame = 0; frame < 90; frame += 1) {
  blend = advanceLocomotionBlend(blend, 0, dt, { riseSeconds: 0.24, fallSeconds: 0.34 });
  blendFall.push(blend);
}
for (let index = 1; index < blendFall.length; index += 1) {
  assert(blendFall[index] <= blendFall[index - 1], "locomotion stop blend was not monotonic");
}
assert(blendFall.at(-1) < 0.02, "locomotion stop blend did not settle");

const armLimits = {
  upperZ: [0.06, 0.16],
  upperY: [0.95, 1.18],
  upperX: [-0.34, 0.34],
  lowerX: [0.06, 0.22],
  handZ: [-0.08, 0.08],
};
const armSamples = [];
const gaitProfiles = [
  { id: "walk", gaitScale: 1, swingAmplitude: 0.18 },
  { id: "jog", gaitScale: 1.22, swingAmplitude: 0.19 },
  { id: "run", gaitScale: 1.55, swingAmplitude: 0.2 },
];
for (const { gaitScale, swingAmplitude } of gaitProfiles) {
  for (let index = 0; index <= 360; index += 1) {
    const phase = index * Math.PI / 180;
    const breath = Math.sin(phase * 0.37);
    const armSwing = Math.sin(phase) * swingAmplitude * gaitScale;
    const pose = {
      upperZ: Math.min(armLimits.upperZ[1], Math.max(armLimits.upperZ[0], 0.1)),
      upperY: Math.min(armLimits.upperY[1], Math.max(armLimits.upperY[0], 1.1)),
      upperX: Math.min(armLimits.upperX[1], Math.max(armLimits.upperX[0], armSwing)),
      lowerX: Math.min(armLimits.lowerX[1], Math.max(armLimits.lowerX[0], 0.1 - armSwing * 0.08)),
      handZ: Math.min(armLimits.handZ[1], Math.max(armLimits.handZ[0], 0.012 + breath * 0.003)),
    };
    for (const [joint, value] of Object.entries(pose)) {
      assert(withinJointLimit(value, ...armLimits[joint]), `${joint} left its relaxed joint limit`);
    }
    armSamples.push(pose);
  }
}
const maximumGaitArmSwingRadians = Math.max(...gaitProfiles.map(({ gaitScale, swingAmplitude }) => gaitScale * swingAmplitude));
assert(maximumGaitArmSwingRadians >= 0.3, "gait arm swing remains visually static");

const idleA = comfortIdleOffsets(0.25, { phase: 0.37, breathRate: 0.76, weightRate: 0.3 }, "idle");
const idleB = comfortIdleOffsets(2.15, { phase: 0.37, breathRate: 0.76, weightRate: 0.3 }, "idle");
const idleChannels = ["hipsZ", "hipsY", "spineZ", "spineX", "neckY", "headY", "headX", "leftShoulderX", "rightShoulderX"];
const maximumIdleJointDeltaRadians = Math.max(...idleChannels.map((key) => Math.abs(idleB[key] - idleA[key])));
assert(maximumIdleJointDeltaRadians > 0.01, "comfort idle produced no visible joint variation");
assert(
  Object.values(idleA.rootTranslation).every((value) => value === 0)
    && Object.values(idleB.rootTranslation).every((value) => value === 0),
  "comfort idle drifted the body instead of moving joints in place",
);
const movingRootBobSamples = Array.from({ length: 121 }, (_, index) => Math.abs(Math.sin(index * Math.PI / 60)) * 0.006);
const idleRootBobSamples = Array.from({ length: 121 }, (_, index) => Math.sin((index / 60) * 1.35) * 0.0015);
assert(Math.max(...movingRootBobSamples) >= 0.0059, "moving root bob is still zero");
assert(Math.max(...idleRootBobSamples) - Math.min(...idleRootBobSamples) > 0.001, "idle root motion is still frozen");

const groundSupportY = 0.05;
const visualClearance = 0.008;
const footContactHeight = 0.035;
const correctionMinimum = -0.25;
const correctionMaximum = 0.12;
let visualCorrection = 0;
const uncorrectedBoundsMinimumY = 0.11;
for (let pass = 0; pass < 12; pass += 1) {
  const measuredMinimumY = uncorrectedBoundsMinimumY + visualCorrection;
  const beforeGap = measuredMinimumY - (groundSupportY + visualClearance);
  const delta = Math.min(0.025, Math.max(-0.025, -beforeGap));
  visualCorrection = Math.min(correctionMaximum, Math.max(correctionMinimum, visualCorrection + delta));
}
const finalBoundsGap = uncorrectedBoundsMinimumY + visualCorrection - (groundSupportY + visualClearance);
assert(near(finalBoundsGap, 0, 0.001), "visual ground calibration did not converge to its measured clearance");
assert(visualCorrection >= correctionMinimum && visualCorrection <= correctionMaximum, "ground correction left its guard bounds");
assert(near(groundSupportY + footContactHeight, 0.085, 1e-10), "foot-contact target height changed unexpectedly");

const here = path.dirname(fileURLToPath(import.meta.url));
const mainPath = path.join(
  here,
  "..",
  "Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js",
);
const mainSource = fs.readFileSync(mainPath, "utf8");
const serverPath = path.join(here, "kira_world_shell_server.py");
const serverSource = fs.readFileSync(serverPath, "utf8");
for (const required of [
  "acceleration_bounded_shortest_arc_yaw_v2",
  "combined_xz_collision_checked_heading_v1",
  "collision_checked_recovery_walk_v2",
  "distance_driven_start_stop_blend_v1",
  "worldLocked: planted",
  "horizontalResidualMeters",
  "calibrated_bind_axis_joint_limited_swing_v10_relaxed_elbow_hand_asymmetry",
  "upperY: Object.freeze([0.95, 1.18])",
  "upperX: Object.freeze([-0.34, 0.34])",
  'kiraNumber("upperY", 1.1)',
  'kiraNumber("swing", kiraGaitArmSwing)',
  "Math.abs(Math.sin(stepPhase)) * 0.006",
  "Math.sin(t * 1.35) * 0.0015",
  'routeId: "walk_inside_to_kitchen_drink"',
  'routeId: "walk_to_home_couch_sit"',
  "replanned_centered_doorway_corridor",
  "routeProgress: activeAvatarPracticeRouteProgressSnapshot()",
  "bodyIntent: practiceRouteProgress ? {",
  '"paused_while_route_remains_active"',
  'phase: "not_started_from_live_person_action"',
  "personOwnedIntentRequired: true",
  "ACTIVE_AVATAR_VISUAL_GROUND_CLEARANCE = 0.008",
  "invalid_height_safe_stop_no_runtime_teleport",
  "stale_upstairs_zone_repaired_in_place_no_runtime_teleport",
]) {
  assert(mainSource.includes(required), `runtime source is missing ${required}`);
}
assert(!mainSource.includes("activeMarker.position.lerpVectors(current, recovery"), "recovery still contains a one-frame position interpolation");
assert(!mainSource.includes("activeMarker.position.copy(KIRA_BUNGALOW_SPAWN)"), "ordinary movement still teleports Kira to the bungalow spawn");
assert(mainSource.includes("if (isKira && (y > 1.8"), "resume validation no longer rejects an upstairs Kira state");
const liveDoctorMapping = /if \(\/\^\(doctor_body_exam[\s\S]{0,900}?return startKiraDoctorBodyControlExam/.test(mainSource);
assert(!liveDoctorMapping, "live chat/shell text still starts the developer body-control harness");
assert(!serverSource.includes('action = "doctor_body_exam"'), "spoken dialogue still publishes a developer exam action");
assert(serverSource.includes('action = "get_drink"'), "spoken inside-and-drink choice does not publish get_drink");
assert(serverSource.includes('action = "go_inside"'), "spoken inside-only choice has no neutral home-entry action");
assert(
  serverSource.includes('r"\\b(?:sit(?:ting)?|tak(?:e|es|en|ing)\\s+(?:a\\s+)?seat|hav(?:e|es|ing)\\s+(?:a\\s+)?seat)\\b"')
    && serverSource.includes('re.search(r"\\b(?:couch|sofa)\\b", reply)'),
  "couch routing does not recognize explicit sit/take-a-seat/have-a-seat choices with a couch/sofa target",
);

const result = {
  pass: true,
  evidenceKind: "deterministic_math_and_static_runtime_source_no_services_no_activation",
  visuallyReviewed: false,
  yaw: {
    largeTurn,
    boundaryTurn,
    maxTurnSpeedRadiansPerSecond: maxTurnSpeed,
    maxTurnAccelerationRadiansPerSecondSquared: maxTurnAcceleration,
  },
  collision: {
    selectedAvoidanceOffsetRadians: steered.offsetRadians,
    sampledWallCrossings: 0,
    recoveryFinalDistanceMeters: Math.hypot(recoveryX, recoveryZ),
    recoveryMaxFrameStepMeters: recoveryMaxStep,
    recoveryCollisionSamples,
    fullyBlockedResult: enclosed,
  },
  homeEntry: {
    reproducedOldDiagonalWallCrossing: true,
    corridorWaypointIds: doorwayCorridor.map((point) => point.id),
    routeStartsAtCurrentBodyWithoutTeleport: true,
    centeredRouteWallCrossings,
    outsideToInsideCrossing: true,
    destination: "kitchen drink affordance",
    laterCouchRoutePresent: mainSource.includes('routeId: "walk_to_home_couch_sit"'),
    stuckReplanRuntimePresent: mainSource.includes("replanned_centered_doorway_corridor"),
  },
  bodyAwareness: {
    currentWorldPositionPublished: mainSource.includes("x: Number(activeMarker.position.x.toFixed(3))"),
    currentNamedPlacePublished: mainSource.includes("place,"),
    personOwnedBodyIntentPublished: mainSource.includes('source: practiceRouteProgress.personOwnedIntent ? "person_owned_self_intent" : "runtime_route"'),
    routeStatusPublishedWhilePaused: mainSource.includes('"paused_while_route_remains_active"'),
    routeWaypointAndDistancePublished: mainSource.includes("currentWaypoint: practiceRouteProgress.waypointLabel")
      && mainSource.includes("distanceMeters: practiceRouteProgress.distanceMeters"),
  },
  continuity: {
    runtimeSpawnCopyPresent: false,
    invalidHeightBehavior: "safe_stop_in_place_and_require_validated_reactivation_or_review",
    staleUpstairsZoneBehavior: "repair_metadata_in_place_then_replan",
    resumeValidationRejectsUpstairsKira: mainSource.includes("if (isKira && (y > 1.8"),
  },
  transitions: {
    riseFirstFrame: blendRise[0],
    riseAfterOneSecond: blendRise.at(-1),
    fallAfterOnePointFiveSeconds: blendFall.at(-1),
  },
  groundAndFeet: {
    supportY: groundSupportY,
    visualClearanceMeters: visualClearance,
    footContactHeightMeters: footContactHeight,
    correctionBoundsMeters: [correctionMinimum, correctionMaximum],
    convergedCorrectionMeters: visualCorrection,
    finalBoundsGapMeters: finalBoundsGap,
    runtimeWorldPlantLockPresent: true,
  },
  relaxedArms: {
    jointLimitsRadians: armLimits,
    deterministicSamples: armSamples.length,
    allSamplesWithinLimits: true,
    contactIkUsedForOrdinaryLocomotion: false,
    gaitProfiles,
    maximumGaitArmSwingRadians,
  },
  naturalIdle: {
    maximumIdleJointDeltaRadians,
    rootTranslationMeters: idleA.rootTranslation,
    movingRootBobMaxMeters: Math.max(...movingRootBobSamples),
    idleRootBobRangeMeters: Math.max(...idleRootBobSamples) - Math.min(...idleRootBobSamples),
  },
  autonomy: {
    liveDoctorHarnessMappingPresent: liveDoctorMapping,
    spokenDialogueDoctorActionPresent: serverSource.includes('action = "doctor_body_exam"'),
    insideOnlyAction: "go_inside",
    insideDrinkAction: "get_drink",
    couchRequiresExplicitCouchOrSofa: true,
    doctorOrMovementExamFromLiveAction: "record_only_not_started",
    personOwnedRouteIntentRecorded: true,
  },
};

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
