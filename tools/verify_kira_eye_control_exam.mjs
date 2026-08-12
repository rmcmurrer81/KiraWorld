import assert from "node:assert/strict";
import {
  KIRA_EYE_CONTROL_EXAM_VERSION,
  KIRA_EYE_CONTROL_LIMITS_DEGREES,
  KIRA_EYE_CONTROL_PHASES,
  buildKiraEyeStructuralReport,
  clampKiraEyeDegrees,
  kiraEyeBlinkEnvelope,
  kiraEyeBlinkTargets,
  kiraEyeDirectionTarget,
  kiraEyeExamPhaseAt,
  kiraEyeSideTargets,
} from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/eye_control_exam.js";

assert.equal(KIRA_EYE_CONTROL_EXAM_VERSION, "3.3.0");
assert.equal(clampKiraEyeDegrees(99, KIRA_EYE_CONTROL_LIMITS_DEGREES.yaw), 13);
assert.equal(clampKiraEyeDegrees(-99, KIRA_EYE_CONTROL_LIMITS_DEGREES.pitch), -7);
assert.equal(kiraEyeDirectionTarget("up").pitch, 7);
assert.equal(kiraEyeDirectionTarget("unknown").id, "center");
assert.deepEqual(kiraEyeSideTargets("near").left, { yaw: 2, pitch: -1 });
assert.deepEqual(kiraEyeSideTargets("near").right, { yaw: -2, pitch: -1 });
assert.deepEqual(kiraEyeBlinkTargets("left", 1), { left: 1, right: 0 });
assert.equal(kiraEyeBlinkEnvelope(0.14, 0.7), 1);
assert.equal(kiraEyeBlinkEnvelope(0.7, 0.7), 0);
assert.equal(kiraEyeExamPhaseAt(0, KIRA_EYE_CONTROL_PHASES).id, "center");
assert.equal(kiraEyeExamPhaseAt(999, KIRA_EYE_CONTROL_PHASES).complete, true);

const fullNames = [
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
  "KiraRightCornea",
];
const structural = buildKiraEyeStructuralReport({
  foundNames: fullNames,
  headBound: true,
  headBoneName: "mixamorig:Head_06",
  oldProceduralNodeCount: 0,
});
assert.equal(structural.complete, true);
assert.equal(structural.headBound, true);
assert.equal(structural.oldProceduralNodeCount, 0);

console.log(JSON.stringify({
  ok: true,
  version: KIRA_EYE_CONTROL_EXAM_VERSION,
  phaseCount: KIRA_EYE_CONTROL_PHASES.length,
  limits: KIRA_EYE_CONTROL_LIMITS_DEGREES,
  structural,
}, null, 2));
