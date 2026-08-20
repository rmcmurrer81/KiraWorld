export const KIRA_DOCTOR_BODY_EXAM_VERSION = "2026-07-18.doctor-body-control-v3";

// These are small diagnostic motions, not claims that a visual pose has passed
// owner review.  A runtime must resolve every named target before it may report
// that phase as supported, and it must measure a non-zero joint delta before it
// may report that the phase executed.
export const KIRA_DOCTOR_JOINT_PHASES = Object.freeze([
  { id: "head_look_left", label: "turn head left", targets: [{ joint: "head", axis: "y", radians: 0.34 }] },
  { id: "head_look_right", label: "turn head right", targets: [{ joint: "head", axis: "y", radians: -0.34 }] },
  { id: "neck_turn_left", label: "turn neck left", targets: [{ joint: "neck", axis: "y", radians: 0.22 }] },
  { id: "neck_turn_right", label: "turn neck right", targets: [{ joint: "neck", axis: "y", radians: -0.22 }] },
  { id: "head_look_up", label: "look up", targets: [{ joint: "head", axis: "x", radians: -0.2 }, { joint: "neck", axis: "x", radians: -0.09 }] },
  { id: "head_look_down", label: "look down", targets: [{ joint: "head", axis: "x", radians: 0.2 }, { joint: "neck", axis: "x", radians: 0.09 }] },
  { id: "left_shoulder", label: "move left shoulder", targets: [{ joint: "leftUpperArm", axis: "x", radians: -0.28 }, { joint: "leftUpperArm", axis: "z", radians: 0.22 }] },
  { id: "right_shoulder", label: "move right shoulder", targets: [{ joint: "rightUpperArm", axis: "x", radians: -0.28 }, { joint: "rightUpperArm", axis: "z", radians: -0.22 }] },
  { id: "left_elbow", label: "bend left elbow", targets: [{ joint: "leftForearm", axis: "x", radians: 0.48 }] },
  { id: "right_elbow", label: "bend right elbow", targets: [{ joint: "rightForearm", axis: "x", radians: 0.48 }] },
  { id: "left_wrist", label: "move left wrist", targets: [{ joint: "leftHand", axis: "x", radians: 0.2 }, { joint: "leftHand", axis: "z", radians: 0.13 }] },
  { id: "right_wrist", label: "move right wrist", targets: [{ joint: "rightHand", axis: "x", radians: 0.2 }, { joint: "rightHand", axis: "z", radians: -0.13 }] },
  ...["thumb", "index", "middle", "ring", "pinky"].flatMap((finger) => ([
    { id: `left_${finger}`, label: `flex left ${finger}`, targets: [{ finger: `L:${finger}`, radians: 0.48 }] },
    { id: `right_${finger}`, label: `flex right ${finger}`, targets: [{ finger: `R:${finger}`, radians: 0.48 }] },
  ])),
  { id: "left_hip", label: "move left hip", targets: [{ joint: "leftThigh", axis: "x", radians: 0.3 }, { joint: "leftThigh", axis: "z", radians: 0.1 }] },
  { id: "right_hip", label: "move right hip", targets: [{ joint: "rightThigh", axis: "x", radians: 0.3 }, { joint: "rightThigh", axis: "z", radians: -0.1 }] },
  { id: "left_knee", label: "bend left knee", targets: [{ joint: "leftShin", axis: "x", radians: -0.42 }] },
  { id: "right_knee", label: "bend right knee", targets: [{ joint: "rightShin", axis: "x", radians: -0.42 }] },
  { id: "left_ankle", label: "move left ankle", targets: [{ joint: "leftFoot", axis: "x", radians: 0.2 }, { joint: "leftFoot", axis: "z", radians: 0.08 }] },
  { id: "right_ankle", label: "move right ankle", targets: [{ joint: "rightFoot", axis: "x", radians: 0.2 }, { joint: "rightFoot", axis: "z", radians: -0.08 }] },
  { id: "left_toes", label: "wiggle left toes", targets: [{ joint: "leftToe", axis: "x", radians: -0.22 }] },
  { id: "right_toes", label: "wiggle right toes", targets: [{ joint: "rightToe", axis: "x", radians: -0.22 }] },
  {
    id: "balance_left",
    label: "balance on left leg",
    targets: [
      { joint: "hips", axis: "z", radians: 0.055 },
      { joint: "rightThigh", axis: "x", radians: 0.2 },
      { joint: "rightShin", axis: "x", radians: -0.24 },
      { joint: "rightFoot", axis: "x", radians: 0.08 },
    ],
  },
  {
    id: "balance_right",
    label: "balance on right leg",
    targets: [
      { joint: "hips", axis: "z", radians: -0.055 },
      { joint: "leftThigh", axis: "x", radians: 0.2 },
      { joint: "leftShin", axis: "x", radians: -0.24 },
      { joint: "leftFoot", axis: "x", radians: 0.08 },
    ],
  },
]);

export const KIRA_DOCTOR_FUNCTIONAL_ACTIONS = Object.freeze([
  { id: "comfort_idle", label: "stand comfortably without translating", requiredJoints: ["hips", "spine", "neck", "head"] },
  { id: "walk", label: "walk", requiredJoints: ["hips", "leftThigh", "leftShin", "leftFoot", "rightThigh", "rightShin", "rightFoot"] },
  { id: "jog", label: "jog", requiredJoints: ["hips", "leftThigh", "leftShin", "leftFoot", "rightThigh", "rightShin", "rightFoot"] },
  { id: "run", label: "run", requiredJoints: ["hips", "leftThigh", "leftShin", "leftFoot", "rightThigh", "rightShin", "rightFoot"] },
  { id: "sit_couch", label: "sit on couch", requiredJoints: ["hips", "spine", "leftThigh", "leftShin", "rightThigh", "rightShin"] },
  { id: "lie_couch", label: "lie on couch", requiredJoints: ["hips", "spine", "neck", "head"] },
  { id: "lie_bed", label: "lie on bed", requiredJoints: ["hips", "spine", "neck", "head"] },
  { id: "lie_ground", label: "lie on current supported ground", requiredJoints: ["hips", "spine", "neck", "head"] },
]);

function targetMissing(target, bones, fingerCounts) {
  if (target.joint) return bones[target.joint] ? [] : [target.joint];
  if (!target.finger) return ["invalid_target"];
  const [side, finger] = target.finger.split(":");
  return Number(fingerCounts?.[side]?.[finger] || 0) > 0 ? [] : [`finger:${side}:${finger}`];
}

export function buildKiraDoctorStructuralReport({ bones = {}, fingerCounts = {} } = {}) {
  const jointPhases = KIRA_DOCTOR_JOINT_PHASES.map((phase) => {
    const missing = [...new Set(phase.targets.flatMap((target) => targetMissing(target, bones, fingerCounts)))];
    return {
      id: phase.id,
      label: phase.label,
      structurallySupported: missing.length === 0,
      missing,
      executed: false,
      passed: false,
      status: missing.length ? "fail_missing_joint" : "not_executed",
    };
  });
  const functionalActions = KIRA_DOCTOR_FUNCTIONAL_ACTIONS.map((action) => {
    const missing = action.requiredJoints.filter((joint) => !bones[joint]);
    return {
      id: action.id,
      label: action.label,
      structurallySupported: missing.length === 0,
      missing,
      executed: false,
      passed: false,
      status: missing.length ? "fail_missing_joint" : "not_executed",
    };
  });
  return {
    version: KIRA_DOCTOR_BODY_EXAM_VERSION,
    jointPhases,
    functionalActions,
    eyeMovement: {
      executed: false,
      passed: false,
      status: "not_tested_separate_eye_rig",
      note: "Head and neck looking are tested here. Eyeball control requires a reviewed eye rig and is never inferred from head motion.",
    },
  };
}

export function comfortIdleOffsets(t, profile = {}, action = "idle") {
  const phase = Number(profile.phase || 0);
  const breathRate = Number(profile.breathRate || 0.76);
  const weightRate = Number(profile.weightRate || 0.3);
  const talking = String(action || "").toLowerCase() === "talking";
  const breath = Math.sin(t * breathRate + phase);
  const weight = Math.sin(t * weightRate + phase * 0.63)
    + Math.sin(t * weightRate * 0.47 + phase * 1.21) * 0.35;
  const gaze = Math.sin(t * 0.23 + phase * 0.91) + Math.sin(t * 0.11 + phase * 1.7) * 0.45;
  // Conversation movement is intentionally asymmetric and intermittent.  A
  // single mirrored sine made both arms look metronomic and left the wrists
  // and fingers visually frozen.  These smooth, identity-seeded envelopes are
  // expression owned by the speaking person; they are never parsed from a
  // user's words as direct motor commands.
  const smoothPositive = (value, threshold = 0.18) => {
    const normalized = Math.max(0, Math.min(1, (value - threshold) / (1 - threshold)));
    return normalized * normalized * (3 - 2 * normalized);
  };
  const leftGesture = talking
    ? smoothPositive(Math.sin(t * 0.73 + phase * 0.41) + Math.sin(t * 0.29 + phase * 1.17) * 0.18)
    : 0;
  const rightGesture = talking
    ? smoothPositive(Math.sin(t * 0.61 + phase * 0.37 + 2.13) + Math.sin(t * 0.33 + phase * 0.82) * 0.16, 0.24)
    : 0;
  const gesture = talking ? leftGesture - rightGesture * 0.82 : 0;
  const wristDriftLeft = Math.sin(t * 0.39 + phase * 0.73) + Math.sin(t * 0.17 + phase * 1.44) * 0.34;
  const wristDriftRight = Math.sin(t * 0.43 + phase * 0.69 + 1.86) + Math.sin(t * 0.19 + phase * 1.03) * 0.31;
  const fingerNames = ["thumb", "index", "middle", "ring", "pinky"];
  const fingerPulse = { L: {}, R: {} };
  for (const [sideIndex, side] of ["L", "R"].entries()) {
    fingerNames.forEach((finger, index) => {
      fingerPulse[side][finger] = Math.sin(t * (0.42 + index * 0.035) + phase + sideIndex * 1.9 + index * 0.74);
    });
  }
  return {
    mode: "person_owned_action_comfort_idle_no_translation_v3",
    breath,
    weight,
    gaze,
    gesture,
    leftGesture,
    rightGesture,
    hipsZ: weight * 0.026,
    hipsY: weight * 0.006,
    spineZ: -weight * 0.017,
    spineX: breath * 0.016,
    neckY: gaze * (talking ? 0.055 : 0.045),
    headY: gaze * (talking ? 0.09 : 0.075),
    headX: breath * 0.012 + (talking ? Math.sin(t * 0.57 + phase) * 0.024 : 0),
    leftShoulderX: leftGesture * 0.115 - rightGesture * 0.018 + weight * 0.022 + breath * 0.014,
    rightShoulderX: rightGesture * 0.102 - leftGesture * 0.016 - weight * 0.019 + breath * 0.012,
    leftShoulderZ: leftGesture * 0.012 - weight * 0.006,
    rightShoulderZ: rightGesture * 0.011 + weight * 0.006,
    leftElbowX: leftGesture * 0.145 + Math.max(0, breath) * 0.018,
    rightElbowX: rightGesture * 0.132 + Math.max(0, -breath) * 0.018,
    leftElbowZ: (leftGesture - rightGesture * 0.25) * 0.018,
    rightElbowZ: (rightGesture - leftGesture * 0.22) * -0.017,
    leftWristX: wristDriftLeft * 0.022 + leftGesture * 0.032,
    rightWristX: wristDriftRight * 0.021 + rightGesture * 0.029,
    leftWristY: wristDriftRight * 0.014,
    rightWristY: -wristDriftLeft * 0.013,
    leftWristZ: wristDriftLeft * 0.013 + leftGesture * 0.016,
    rightWristZ: -wristDriftRight * 0.013 - rightGesture * 0.015,
    fingerStrength: talking ? 0.062 : 0.046,
    leftKneeX: Math.max(0, weight) * 0.02,
    rightKneeX: Math.max(0, -weight) * 0.02,
    leftAnkleX: -Math.max(0, weight) * 0.01,
    rightAnkleX: -Math.max(0, -weight) * 0.01,
    leftToeX: Math.sin(t * 0.37 + phase) * 0.006,
    rightToeX: Math.sin(t * 0.35 + phase + 1.4) * 0.006,
    fingerPulse,
    rootTranslation: Object.freeze({ x: 0, y: 0, z: 0 }),
  };
}

export function summarizeExecutedExam(results = []) {
  const passed = results.filter((result) => result.passed === true).length;
  const failed = results.filter((result) => result.passed !== true).length;
  return { total: results.length, passed, failed, allPassed: results.length > 0 && failed === 0 };
}
