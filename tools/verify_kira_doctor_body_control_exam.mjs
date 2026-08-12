import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  KIRA_DOCTOR_BODY_EXAM_VERSION,
  KIRA_DOCTOR_FUNCTIONAL_ACTIONS,
  KIRA_DOCTOR_JOINT_PHASES,
  buildKiraDoctorStructuralReport,
  comfortIdleOffsets,
} from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/body_control_exam.js";

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

function readGlbJson(filePath) {
  const buffer = fs.readFileSync(filePath);
  assert(buffer.toString("ascii", 0, 4) === "glTF", "Kira body is not a binary glTF file");
  let offset = 12;
  while (offset + 8 <= buffer.length) {
    const length = buffer.readUInt32LE(offset);
    const type = buffer.readUInt32LE(offset + 4);
    if (type === 0x4e4f534a) {
      const text = buffer.subarray(offset + 8, offset + 8 + length)
        .toString("utf8")
        .replace(/[\u0000\u0020]+$/u, "");
      return JSON.parse(text);
    }
    offset += 8 + length;
  }
  throw new Error("Kira body GLB has no JSON chunk");
}

function runtimeRigContextFromGlb(gltf) {
  const nodes = gltf.nodes || [];
  const skinnedNodeIndices = new Set((gltf.skins || []).flatMap((skin) => skin.joints || []));
  const names = [...skinnedNodeIndices]
    .map((index) => nodes[index]?.name || "")
    .filter(Boolean);
  const has = (pattern) => names.some((name) => pattern.test(name));
  const count = (pattern) => names.filter((name) => !/end/i.test(name) && pattern.test(name)).length;
  return {
    names,
    bones: {
      hips: has(/mixamorig:Hips_/i),
      spine: has(/mixamorig:Spine_/i),
      neck: has(/mixamorig:Neck_/i),
      head: has(/mixamorig:Head_/i),
      leftUpperArm: has(/mixamorig:LeftArm_/i),
      leftForearm: has(/mixamorig:LeftForeArm_/i),
      leftHand: has(/mixamorig:LeftHand_/i),
      rightUpperArm: has(/mixamorig:RightArm_/i),
      rightForearm: has(/mixamorig:RightForeArm_/i),
      rightHand: has(/mixamorig:RightHand_/i),
      leftThigh: has(/mixamorig:LeftUpLeg_/i),
      leftShin: has(/mixamorig:LeftLeg_/i),
      leftFoot: has(/mixamorig:LeftFoot_/i),
      leftToe: has(/mixamorig:LeftToeBase_/i),
      rightThigh: has(/mixamorig:RightUpLeg_/i),
      rightShin: has(/mixamorig:RightLeg_/i),
      rightFoot: has(/mixamorig:RightFoot_/i),
      rightToe: has(/mixamorig:RightToeBase_/i),
    },
    fingerCounts: {
      L: {
        thumb: count(/mixamorig:LeftHandThumb[1-4]_/i),
        index: count(/mixamorig:LeftHandIndex[1-4]_/i),
        middle: count(/mixamorig:LeftHandMiddle[1-4]_/i),
        ring: count(/mixamorig:LeftHandRing[1-4]_/i),
        pinky: count(/mixamorig:LeftHandPinky[1-4]_/i),
      },
      R: {
        thumb: count(/mixamorig:RightHandThumb[1-4]_/i),
        index: count(/mixamorig:RightHandIndex[1-4]_/i),
        middle: count(/mixamorig:RightHandMiddle[1-4]_/i),
        ring: count(/mixamorig:RightHandRing[1-4]_/i),
        pinky: count(/mixamorig:RightHandPinky[1-4]_/i),
      },
    },
  };
}

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, "..");
const bodyPath = path.join(root, "Avatar/models/temp_ai/kira/avatar.glb");
const mainPath = path.join(
  root,
  "Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js",
);
const gltf = readGlbJson(bodyPath);
const context = runtimeRigContextFromGlb(gltf);
const structural = buildKiraDoctorStructuralReport(context);

assert(KIRA_DOCTOR_JOINT_PHASES.length === 32, "doctor exam joint phase count changed unexpectedly");
assert(KIRA_DOCTOR_FUNCTIONAL_ACTIONS.length === 8, "doctor exam functional action count changed unexpectedly");
for (const phase of structural.jointPhases) {
  assert(phase.structurallySupported, `${phase.id} is missing from Kira's exact skinned rig: ${phase.missing.join(", ")}`);
  assert(phase.status === "not_executed" && phase.passed === false, `${phase.id} was falsely promoted from structure to execution`);
}
for (const action of structural.functionalActions) {
  assert(action.structurallySupported, `${action.id} is missing required joints`);
  assert(action.status === "not_executed" && action.passed === false, `${action.id} was falsely reported as executed`);
}
for (const side of ["L", "R"]) {
  for (const finger of ["thumb", "index", "middle", "ring", "pinky"]) {
    assert(context.fingerCounts[side][finger] === 4, `${side} ${finger} does not have four controllable phalanges`);
  }
}

const missingToeContext = JSON.parse(JSON.stringify(context));
missingToeContext.bones.leftToe = false;
const missingToe = buildKiraDoctorStructuralReport(missingToeContext).jointPhases.find((item) => item.id === "left_toes");
assert(missingToe.status === "fail_missing_joint" && missingToe.passed === false, "missing toe negative control did not fail honestly");

const profile = { phase: 0.73, breathRate: 0.76, weightRate: 0.3 };
const idleSamples = [];
const talkingSamples = [];
for (let time = 0; time <= 24; time += 0.2) {
  idleSamples.push(comfortIdleOffsets(time, profile, "idle"));
  talkingSamples.push(comfortIdleOffsets(time, profile, "talking"));
}
for (const sample of [...idleSamples, ...talkingSamples]) {
  assert(sample.rootTranslation.x === 0 && sample.rootTranslation.y === 0 && sample.rootTranslation.z === 0, "comfort idle requested root translation");
}
const maxAbs = (samples, key) => Math.max(...samples.map((sample) => Math.abs(sample[key])));
assert(maxAbs(idleSamples, "hipsZ") > 0.02, "idle weight shift is below the deterministic visibility floor");
assert(maxAbs(idleSamples, "headY") > 0.06, "idle gaze is below the deterministic visibility floor");
assert(maxAbs(idleSamples, "leftShoulderX") > 0.02, "idle shoulder motion is below the deterministic visibility floor");
assert(maxAbs(talkingSamples, "leftShoulderX") > maxAbs(idleSamples, "leftShoulderX"), "talking does not add a stronger shoulder gesture");
assert(maxAbs(talkingSamples, "headY") > maxAbs(idleSamples, "headY"), "talking does not add a stronger gaze motion");
const indexPulseRange = Math.max(...idleSamples.map((sample) => sample.fingerPulse.L.index))
  - Math.min(...idleSamples.map((sample) => sample.fingerPulse.L.index));
assert(indexPulseRange > 1.5, "individual finger pulse did not vary over time");

const mainSource = fs.readFileSync(mainPath, "utf8");
for (const required of [
  "startKiraDoctorBodyControlExam",
  "probeKiraDoctorJointControl",
  "pass_measured_joint_delta",
  "mindOrLifeLoopActivatedByProbe: false",
  "/^(doctor_body_exam|doctor_body_control_exam|body_control_exam|movement_exam)$/",
  "startActiveAvatarWalkPractice",
  "startActiveAvatarJogPractice",
  "startActiveAvatarRunPractice",
  "startActiveAvatarGroundLieHold",
  "clear_supported_body_length_floor_area_required",
  "positionChangedForPosture: false",
  "comfortIdleRootTranslation: comfortIdle.rootTranslation",
  "leftUpperArm: rotation(activeAvatarProceduralRig.bones?.leftUpperArm)",
  "rightForearm: rotation(activeAvatarProceduralRig.bones?.rightForearm)",
  "leftIndex: rotation(activeAvatarProceduralRig.fingers?.L?.index?.[0])",
  "rightPinky: rotation(activeAvatarProceduralRig.fingers?.R?.pinky?.[0])",
  "leftToe: activeAvatarProceduralFindBone",
  "rightToe: activeAvatarProceduralFindBone",
]) {
  assert(mainSource.includes(required), `Home World runtime is missing integration token: ${required}`);
}
const groundStart = mainSource.indexOf("function startActiveAvatarGroundLieHold");
const groundEnd = mainSource.indexOf("function activeAvatarRecordVoluntaryActionBlock", groundStart);
const groundSection = mainSource.slice(groundStart, groundEnd);
assert(groundStart >= 0 && groundEnd > groundStart, "ground-lie function could not be isolated");
assert(!/activeMarker\.position\.(?:copy|set|lerp)/.test(groundSection), "ground lie directly rewrites Kira's world position");

const result = {
  pass: true,
  version: KIRA_DOCTOR_BODY_EXAM_VERSION,
  evidenceKind: "exact_glb_skin_inventory_plus_deterministic_offsets_plus_static_runtime_integration",
  visuallyReviewed: false,
  rig: {
    skinnedJointCount: context.names.length,
    animationClipCount: (gltf.animations || []).length,
    allDoctorJointTargetsPresent: true,
    fingerPhalangesPerFinger: context.fingerCounts,
    toeControl: "one toe-base joint per foot; individual toes are not independently rigged",
  },
  exam: {
    jointPhases: structural.jointPhases.length,
    structurallySupported: structural.jointPhases.filter((item) => item.structurallySupported).length,
    executedByThisOfflineCheck: 0,
    falselyPromotedToPass: 0,
    negativeControl: missingToe,
    eyeMovement: structural.eyeMovement,
  },
  comfortIdle: {
    sampleCount: idleSamples.length,
    rootTranslationRequested: { x: 0, y: 0, z: 0 },
    maxIdleHipsRadians: maxAbs(idleSamples, "hipsZ"),
    maxIdleHeadYawRadians: maxAbs(idleSamples, "headY"),
    maxIdleShoulderRadians: maxAbs(idleSamples, "leftShoulderX"),
    maxTalkingShoulderRadians: maxAbs(talkingSamples, "leftShoulderX"),
    individualFingerPulseRange: indexPulseRange,
    note: "Numerically non-zero and deliberately visible-scale; a real-browser visual review is still required.",
  },
  functionalActions: structural.functionalActions,
  groundLie: {
    samplesRequiredAtRuntime: 15,
    directPositionRewritePresent: false,
    status: "implemented_but_not_claimed_pass_by_offline_check",
  },
  limitations: [
    "Kira's GLB has no authored animation clips; motion is procedural.",
    "Structural support is not a visual-naturalness pass.",
    "Couch, bed, walk, jog, run, and ground-lie completion need isolated runtime evidence before pass.",
  ],
};

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
