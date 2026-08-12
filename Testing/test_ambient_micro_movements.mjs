import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  AMBIENT_MICRO_MOVEMENT_LIMITS,
  ambientMicroMovementFrame,
  ambientMicroMovementIsWithinLimits,
  ambientMicroMovementSuppression,
  buildAmbientMicroMovementProfile,
} from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/ambient_micro_movements.js";

const MAIN_URL = new URL(
  "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js",
  import.meta.url,
);

test("Kira's ambient samples are deterministic, bounded, and never emit root or scale movement", () => {
  const profile = buildAmbientMicroMovementProfile("kira");
  for (let index = 0; index < 2400; index += 1) {
    const input = {
      seconds: index * 0.071,
      identity: "kira",
      profile,
      action: "idle",
      supportsExistingMouthSmile: true,
    };
    const first = ambientMicroMovementFrame(input);
    const second = ambientMicroMovementFrame(input);
    assert.deepEqual(first, second);
    assert.equal(ambientMicroMovementIsWithinLimits(first), true);
    assert.deepEqual(first.rootTranslation, { x: 0, y: 0, z: 0 });
    assert.deepEqual(first.rootRotation, { x: 0, y: 0, z: 0 });
    assert.deepEqual(first.scaleDelta, { x: 0, y: 0, z: 0 });
    assert.equal(first.fingerPulseIsRadians, true);
  }
});

test("identity profiles are stable but person-specific", () => {
  assert.deepEqual(buildAmbientMicroMovementProfile("kira"), buildAmbientMicroMovementProfile("kira"));
  assert.notDeepEqual(buildAmbientMicroMovementProfile("kira"), buildAmbientMicroMovementProfile("kathryn_merteuil"));
});

test("deliberate actions pause ambient joints and locomotion strongly attenuates them", () => {
  const idle = ambientMicroMovementFrame({ seconds: 17.3, identity: "kira", action: "idle" });
  const deliberate = ambientMicroMovementFrame({
    seconds: 17.3,
    identity: "kira",
    action: "pick_up_tablet",
    deliberateAction: true,
    supportsExistingMouthSmile: true,
  });
  const walking = ambientMicroMovementFrame({
    seconds: 17.3,
    identity: "kira",
    action: "walk",
    locomotionBlend: 1,
    supportsExistingMouthSmile: true,
  });
  assert.equal(deliberate.suppression.body, 0);
  assert.equal(deliberate.suppression.hands, 0);
  assert.equal(deliberate.face.smile, 0);
  for (const field of [
    "hipsZ", "hipsY", "spineZ", "spineX", "neckY", "neckZ", "headY", "headX", "headZ",
    "leftShoulderX", "rightShoulderX", "leftElbowX", "rightElbowX",
    "leftWristX", "rightWristX", "leftKneeX", "rightKneeX", "leftToeX", "rightToeX",
  ]) assert.equal(deliberate[field], 0, `${field} must pause for deliberate action`);
  assert.equal(walking.suppression.body, 0.08);
  assert.equal(walking.suppression.hands, 0);
  assert.ok(Math.abs(walking.headY) <= Math.abs(idle.headY) + 1e-12);
  assert.equal(walking.fingerStrength, 0);
  assert.equal(walking.face.smile, 0);
});

test("actual lip sync suppresses ambient smile and attenuates body motion", () => {
  const idleFrames = Array.from({ length: 1200 }, (_, index) => ambientMicroMovementFrame({
    seconds: index * 0.09,
    identity: "kira",
    action: "idle",
    supportsExistingMouthSmile: true,
  }));
  assert.ok(Math.max(...idleFrames.map((frame) => frame.face.smile)) > 0.08);
  const talking = ambientMicroMovementFrame({
    seconds: 21,
    identity: "kira",
    action: "talking",
    lipSyncActive: true,
    supportsExistingMouthSmile: true,
  });
  assert.equal(talking.face.smile, 0);
  assert.equal(talking.face.suppressedDuringLipSync, true);
  assert.equal(talking.suppression.body, 0.42);
  assert.equal(talking.suppression.hands, 0.36);
});

test("no-drift integration restores the exact bind pose before adding each local frame", async () => {
  const source = await readFile(MAIN_URL, "utf8");
  const updateStart = source.indexOf("function updateActiveAvatarProceduralRig(t)");
  const updateEnd = source.indexOf("async function loadActivePoseManifest", updateStart);
  const update = source.slice(updateStart, updateEnd);
  const resetAt = update.indexOf("resetActiveAvatarProceduralRigPose(rig)");
  const sampleAt = update.indexOf("ambientMicroMovementFrame({");
  const firstJointAt = update.indexOf("rig.bones.hips.rotation.z +=");
  assert.ok(resetAt >= 0);
  assert.ok(sampleAt >= 0);
  assert.ok(firstJointAt >= 0);
  assert.ok(sampleAt < resetAt, "the pure frame may be sampled before reset");
  assert.ok(resetAt < firstJointAt, "the exact bind pose must be restored before any ambient joint delta");
  assert.equal(source.includes("activeAvatarRoot.scale.add"), false);
  assert.equal(source.includes("activeMarker.position.add(comfortIdle"), false);
});

test("module limits remain intentionally small", () => {
  assert.ok(AMBIENT_MICRO_MOVEMENT_LIMITS.headY <= 0.05);
  assert.ok(AMBIENT_MICRO_MOVEMENT_LIMITS.wristX <= 0.02);
  assert.ok(AMBIENT_MICRO_MOVEMENT_LIMITS.finger <= 0.03);
  assert.deepEqual(ambientMicroMovementSuppression({ action: "lie_on_bed" }), {
    reason: "paused_for_person_owned_deliberate_action",
    body: 0,
    hands: 0,
    face: 0,
    locomotion: false,
    deliberate: true,
    lipSyncActive: false,
  });
});
