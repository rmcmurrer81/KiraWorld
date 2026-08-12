import assert from "node:assert/strict";
import test from "node:test";

import { comfortIdleOffsets } from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/body_control_exam.js";

const profile = Object.freeze({ phase: 1.37, breathRate: 0.74, weightRate: 0.29 });

test("comfort motion is deterministic, joint-only, and never translates the person", () => {
  for (let index = 0; index < 80; index += 1) {
    const seconds = index * 0.19;
    const first = comfortIdleOffsets(seconds, profile, "idle");
    const second = comfortIdleOffsets(seconds, profile, "idle");
    assert.deepEqual(first, second);
    assert.deepEqual(first.rootTranslation, { x: 0, y: 0, z: 0 });
    assert.equal(first.mode, "person_owned_action_comfort_idle_no_translation_v3");
  }
});

test("actual speaking expression can move shoulders, elbows, wrists, and fingers asymmetrically", () => {
  const samples = Array.from({ length: 180 }, (_, index) => (
    comfortIdleOffsets(index * 0.08, profile, "talking")
  ));
  const maxAbs = (name) => Math.max(...samples.map((sample) => Math.abs(sample[name])));
  assert.ok(maxAbs("leftShoulderX") > 0.08);
  assert.ok(maxAbs("rightShoulderX") > 0.07);
  assert.ok(maxAbs("leftElbowX") > 0.09);
  assert.ok(maxAbs("rightElbowX") > 0.08);
  assert.ok(maxAbs("leftWristX") > 0.02);
  assert.ok(maxAbs("rightWristX") > 0.02);
  assert.ok(samples.some((sample) => Math.abs(sample.leftGesture - sample.rightGesture) > 0.25));
  assert.ok(samples.every((sample) => sample.fingerStrength === 0.062));
  assert.ok(samples.every((sample) => Object.keys(sample.fingerPulse.L).length === 5));
  assert.ok(samples.every((sample) => Object.keys(sample.fingerPulse.R).length === 5));
});

