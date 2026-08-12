export const AMBIENT_MICRO_MOVEMENT_VERSION = "2026-07-19.person-owned-ambient-v1";

export const AMBIENT_MICRO_MOVEMENT_LIMITS = Object.freeze({
  hipsZ: 0.016,
  hipsY: 0.005,
  spineZ: 0.012,
  spineX: 0.011,
  neckY: 0.027,
  neckZ: 0.014,
  headY: 0.045,
  headX: 0.018,
  headZ: 0.022,
  shoulderX: 0.034,
  shoulderZ: 0.018,
  elbowX: 0.034,
  elbowZ: 0.012,
  wristX: 0.016,
  wristY: 0.011,
  wristZ: 0.013,
  kneeX: 0.012,
  ankleX: 0.006,
  toeX: 0.004,
  finger: 0.026,
  smile: 0.24,
});

const IDLE_ACTIONS = new Set(["", "idle", "neutral", "stand", "standing", "comfort_idle"]);
const LOCOMOTION_ACTIONS = new Set(["walk", "jog", "run", "dodge", "swim", "swim_idle", "locomotion"]);
const TALK_ACTIONS = new Set(["talk", "talking", "speak", "speaking"]);
const FINGERS = Object.freeze(["thumb", "index", "middle", "ring", "pinky"]);

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, Number(value) || 0));
}

function smoothPositive(value, threshold = 0.55) {
  const normalized = clamp((value - threshold) / Math.max(1e-6, 1 - threshold), 0, 1);
  return normalized * normalized * (3 - 2 * normalized);
}

function hashIdentity(identity) {
  const value = String(identity || "synthetic-person").trim().toLowerCase();
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

export function buildAmbientMicroMovementProfile(identity = "synthetic-person") {
  const seed = hashIdentity(identity);
  return Object.freeze({
    identity: String(identity || "synthetic-person"),
    seed,
    phase: (seed / 0xffffffff) * Math.PI * 2,
    breathRate: 0.64 + ((seed >>> 7) % 17) / 100,
    weightRate: 0.19 + ((seed >>> 14) % 9) / 100,
    settleRate: 0.105 + ((seed >>> 21) % 7) / 1000,
    mode: "deterministic_identity_seeded_ambient_profile_v1",
  });
}

export function ambientMicroMovementSuppression({
  action = "idle",
  locomotionBlend = 0,
  deliberateAction = false,
  lipSyncActive = false,
} = {}) {
  const normalizedAction = String(action || "idle").trim().toLowerCase();
  const locomotion = LOCOMOTION_ACTIONS.has(normalizedAction) || clamp(locomotionBlend, 0, 1) > 0.012;
  const deliberate = !!deliberateAction
    || (!IDLE_ACTIONS.has(normalizedAction) && !TALK_ACTIONS.has(normalizedAction) && !LOCOMOTION_ACTIONS.has(normalizedAction));
  if (deliberate) {
    return Object.freeze({
      reason: "paused_for_person_owned_deliberate_action",
      body: 0,
      hands: 0,
      face: 0,
      locomotion: false,
      deliberate: true,
      lipSyncActive: !!lipSyncActive,
    });
  }
  if (locomotion) {
    return Object.freeze({
      reason: "strongly_attenuated_during_locomotion",
      body: 0.08,
      hands: 0,
      face: 0,
      locomotion: true,
      deliberate: false,
      lipSyncActive: !!lipSyncActive,
    });
  }
  if (lipSyncActive || TALK_ACTIONS.has(normalizedAction)) {
    return Object.freeze({
      reason: lipSyncActive ? "attenuated_during_actual_voice_playback" : "attenuated_during_talking_pose",
      body: lipSyncActive ? 0.42 : 0.56,
      hands: lipSyncActive ? 0.36 : 0.5,
      face: 0,
      locomotion: false,
      deliberate: false,
      lipSyncActive: !!lipSyncActive,
    });
  }
  return Object.freeze({
    reason: "ambient_idle",
    body: 1,
    hands: 1,
    face: 1,
    locomotion: false,
    deliberate: false,
    lipSyncActive: false,
  });
}

function bounded(value, limit, intensity = 1) {
  const safeLimit = Math.abs(Number(limit) || 0);
  return clamp(value * clamp(intensity, 0, 1), -safeLimit, safeLimit);
}

/**
 * Produces person-owned ambient expression as local joint deltas only.
 *
 * This is not a command parser or an activity planner. The caller supplies the
 * person's current action, and deliberate actions take precedence. No root
 * position, world heading, bone scale, or mesh scale is ever emitted.
 */
export function ambientMicroMovementFrame({
  seconds = 0,
  identity = "synthetic-person",
  profile = null,
  action = "idle",
  locomotionBlend = 0,
  deliberateAction = false,
  lipSyncActive = false,
  supportsExistingMouthSmile = false,
} = {}) {
  const t = Math.max(0, Number(seconds) || 0);
  const p = profile || buildAmbientMicroMovementProfile(identity);
  const phase = Number.isFinite(Number(p.phase)) ? Number(p.phase) : buildAmbientMicroMovementProfile(identity).phase;
  const suppression = ambientMicroMovementSuppression({ action, locomotionBlend, deliberateAction, lipSyncActive });
  const breath = Math.sin(t * Number(p.breathRate || 0.7) + phase);
  const weight = (
    Math.sin(t * Number(p.weightRate || 0.23) + phase * 0.61)
    + Math.sin(t * Number(p.weightRate || 0.23) * 0.43 + phase * 1.39) * 0.28
  ) / 1.28;
  const settle = (
    Math.sin(t * Number(p.settleRate || 0.11) + phase * 0.83)
    + Math.sin(t * 0.071 + phase * 1.63) * 0.34
  ) / 1.34;
  const glance = (
    Math.sin(t * 0.181 + phase * 0.47)
    + Math.sin(t * 0.097 + phase * 1.71) * 0.32
  ) / 1.32;
  const headTiltEvent = smoothPositive(Math.sin(t * 0.123 + phase * 1.27), 0.62)
    - smoothPositive(Math.sin(t * 0.109 + phase * 0.43 + 2.2), 0.7) * 0.72;
  const handSettleLeft = (
    Math.sin(t * 0.211 + phase * 0.73)
    + Math.sin(t * 0.089 + phase * 1.42) * 0.26
  ) / 1.26;
  const handSettleRight = (
    Math.sin(t * 0.193 + phase * 0.31 + 1.91)
    + Math.sin(t * 0.081 + phase * 1.11) * 0.29
  ) / 1.29;
  const shoulderSettleLeft = smoothPositive(Math.sin(t * 0.157 + phase * 0.39), 0.69);
  const shoulderSettleRight = smoothPositive(Math.sin(t * 0.149 + phase * 0.91 + 2.07), 0.72);
  const body = suppression.body;
  const hands = suppression.hands;
  const fingerPulse = { L: {}, R: {} };
  for (const [sideIndex, side] of ["L", "R"].entries()) {
    FINGERS.forEach((finger, index) => {
      const primary = Math.sin(t * (0.27 + index * 0.019) + phase * (1 + index * 0.07) + sideIndex * 1.83 + index * 0.71);
      const secondary = Math.sin(t * (0.103 + index * 0.006) + phase * 0.67 + sideIndex * 0.91) * 0.21;
      fingerPulse[side][finger] = bounded((primary + secondary) / 1.21, AMBIENT_MICRO_MOVEMENT_LIMITS.finger, hands);
    });
  }
  const smilePulse = smoothPositive(Math.sin(t * 0.137 + phase * 1.19), 0.72);
  const smile = supportsExistingMouthSmile
    ? bounded(smilePulse, AMBIENT_MICRO_MOVEMENT_LIMITS.smile, suppression.face)
    : 0;
  return Object.freeze({
    version: AMBIENT_MICRO_MOVEMENT_VERSION,
    mode: "person_owned_ambient_micro_movement_no_translation_no_scale_v1",
    identity: String(p.identity || identity || "synthetic-person"),
    profile: p,
    action: String(action || "idle"),
    suppression,
    breath,
    weight,
    gaze: glance,
    gesture: handSettleLeft - handSettleRight,
    leftGesture: Math.max(0, handSettleLeft),
    rightGesture: Math.max(0, handSettleRight),
    hipsZ: bounded(weight, AMBIENT_MICRO_MOVEMENT_LIMITS.hipsZ, body),
    hipsY: bounded(settle, AMBIENT_MICRO_MOVEMENT_LIMITS.hipsY, body),
    spineZ: bounded(-weight, AMBIENT_MICRO_MOVEMENT_LIMITS.spineZ, body),
    spineX: bounded(breath, AMBIENT_MICRO_MOVEMENT_LIMITS.spineX, body),
    neckY: bounded(glance * 0.72, AMBIENT_MICRO_MOVEMENT_LIMITS.neckY, body),
    neckZ: bounded(headTiltEvent * 0.65, AMBIENT_MICRO_MOVEMENT_LIMITS.neckZ, body),
    headY: bounded(glance, AMBIENT_MICRO_MOVEMENT_LIMITS.headY, body),
    headX: bounded(breath * 0.42 + settle * 0.31, AMBIENT_MICRO_MOVEMENT_LIMITS.headX, body),
    headZ: bounded(headTiltEvent, AMBIENT_MICRO_MOVEMENT_LIMITS.headZ, body),
    leftShoulderX: bounded(weight * 0.34 + breath * 0.25 + shoulderSettleLeft, AMBIENT_MICRO_MOVEMENT_LIMITS.shoulderX, body),
    rightShoulderX: bounded(-weight * 0.31 + breath * 0.22 + shoulderSettleRight, AMBIENT_MICRO_MOVEMENT_LIMITS.shoulderX, body),
    leftShoulderZ: bounded(-weight * 0.35 + headTiltEvent * 0.18, AMBIENT_MICRO_MOVEMENT_LIMITS.shoulderZ, body),
    rightShoulderZ: bounded(weight * 0.34 - headTiltEvent * 0.16, AMBIENT_MICRO_MOVEMENT_LIMITS.shoulderZ, body),
    leftElbowX: bounded(Math.max(0, handSettleLeft) * 0.72 + Math.max(0, breath) * 0.18, AMBIENT_MICRO_MOVEMENT_LIMITS.elbowX, hands),
    rightElbowX: bounded(Math.max(0, handSettleRight) * 0.7 + Math.max(0, -breath) * 0.18, AMBIENT_MICRO_MOVEMENT_LIMITS.elbowX, hands),
    leftElbowZ: bounded((handSettleLeft - handSettleRight * 0.2) * 0.3, AMBIENT_MICRO_MOVEMENT_LIMITS.elbowZ, hands),
    rightElbowZ: bounded((handSettleRight - handSettleLeft * 0.2) * -0.3, AMBIENT_MICRO_MOVEMENT_LIMITS.elbowZ, hands),
    leftWristX: bounded(handSettleLeft, AMBIENT_MICRO_MOVEMENT_LIMITS.wristX, hands),
    rightWristX: bounded(handSettleRight, AMBIENT_MICRO_MOVEMENT_LIMITS.wristX, hands),
    leftWristY: bounded(handSettleRight * 0.62, AMBIENT_MICRO_MOVEMENT_LIMITS.wristY, hands),
    rightWristY: bounded(-handSettleLeft * 0.58, AMBIENT_MICRO_MOVEMENT_LIMITS.wristY, hands),
    leftWristZ: bounded(handSettleLeft * 0.71, AMBIENT_MICRO_MOVEMENT_LIMITS.wristZ, hands),
    rightWristZ: bounded(-handSettleRight * 0.68, AMBIENT_MICRO_MOVEMENT_LIMITS.wristZ, hands),
    fingerStrength: AMBIENT_MICRO_MOVEMENT_LIMITS.finger * hands,
    fingerPulseIsRadians: true,
    leftKneeX: bounded(Math.max(0, weight), AMBIENT_MICRO_MOVEMENT_LIMITS.kneeX, body),
    rightKneeX: bounded(Math.max(0, -weight), AMBIENT_MICRO_MOVEMENT_LIMITS.kneeX, body),
    leftAnkleX: bounded(-Math.max(0, weight), AMBIENT_MICRO_MOVEMENT_LIMITS.ankleX, body),
    rightAnkleX: bounded(-Math.max(0, -weight), AMBIENT_MICRO_MOVEMENT_LIMITS.ankleX, body),
    leftToeX: bounded(Math.sin(t * 0.29 + phase), AMBIENT_MICRO_MOVEMENT_LIMITS.toeX, hands),
    rightToeX: bounded(Math.sin(t * 0.281 + phase + 1.37), AMBIENT_MICRO_MOVEMENT_LIMITS.toeX, hands),
    fingerPulse,
    face: Object.freeze({
      smile,
      existingMouthOnly: true,
      createdMouthMeshes: 0,
      suppressedDuringLipSync: !!lipSyncActive,
    }),
    rootTranslation: Object.freeze({ x: 0, y: 0, z: 0 }),
    rootRotation: Object.freeze({ x: 0, y: 0, z: 0 }),
    scaleDelta: Object.freeze({ x: 0, y: 0, z: 0 }),
  });
}

export function ambientMicroMovementIsWithinLimits(frame) {
  if (!frame || frame.rootTranslation?.x || frame.rootTranslation?.y || frame.rootTranslation?.z) return false;
  if (frame.rootRotation?.x || frame.rootRotation?.y || frame.rootRotation?.z) return false;
  if (frame.scaleDelta?.x || frame.scaleDelta?.y || frame.scaleDelta?.z) return false;
  const checks = [
    ["hipsZ", "hipsZ"], ["hipsY", "hipsY"], ["spineZ", "spineZ"], ["spineX", "spineX"],
    ["neckY", "neckY"], ["neckZ", "neckZ"], ["headY", "headY"], ["headX", "headX"], ["headZ", "headZ"],
    ["leftShoulderX", "shoulderX"], ["rightShoulderX", "shoulderX"],
    ["leftShoulderZ", "shoulderZ"], ["rightShoulderZ", "shoulderZ"],
    ["leftElbowX", "elbowX"], ["rightElbowX", "elbowX"], ["leftElbowZ", "elbowZ"], ["rightElbowZ", "elbowZ"],
    ["leftWristX", "wristX"], ["rightWristX", "wristX"], ["leftWristY", "wristY"], ["rightWristY", "wristY"],
    ["leftWristZ", "wristZ"], ["rightWristZ", "wristZ"],
    ["leftKneeX", "kneeX"], ["rightKneeX", "kneeX"], ["leftAnkleX", "ankleX"], ["rightAnkleX", "ankleX"],
    ["leftToeX", "toeX"], ["rightToeX", "toeX"],
  ];
  if (checks.some(([field, limit]) => Math.abs(Number(frame[field]) || 0) > AMBIENT_MICRO_MOVEMENT_LIMITS[limit] + 1e-12)) return false;
  if (Math.abs(Number(frame.face?.smile) || 0) > AMBIENT_MICRO_MOVEMENT_LIMITS.smile + 1e-12) return false;
  return ["L", "R"].every((side) => FINGERS.every((finger) => (
    Math.abs(Number(frame.fingerPulse?.[side]?.[finger]) || 0) <= AMBIENT_MICRO_MOVEMENT_LIMITS.finger + 1e-12
  )));
}
