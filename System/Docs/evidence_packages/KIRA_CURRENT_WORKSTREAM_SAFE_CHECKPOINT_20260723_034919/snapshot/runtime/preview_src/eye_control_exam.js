export const KIRA_EYE_CONTROL_EXAM_VERSION = "3.3.0";

export const KIRA_EYE_CONTROL_LIMITS_DEGREES = Object.freeze({
  // These are controller units mapped to the visually reviewed R7-v3
  // surface-translation envelope: 13 degrees = 1.25 mm horizontally and
  // 7 degrees = 0.72 mm vertically.  The cornea and sclera never move.
  yaw: 13,
  pitch: 7,
  convergence: 2,
});

export const KIRA_EYE_CONTROL_PHASES = Object.freeze([
  Object.freeze({ id: "center", seconds: 0.8 }),
  Object.freeze({ id: "left", seconds: 1.0 }),
  Object.freeze({ id: "center", seconds: 0.5 }),
  Object.freeze({ id: "right", seconds: 1.0 }),
  Object.freeze({ id: "center", seconds: 0.5 }),
  Object.freeze({ id: "up", seconds: 0.9 }),
  Object.freeze({ id: "down", seconds: 0.9 }),
  Object.freeze({ id: "near", seconds: 0.9 }),
  Object.freeze({ id: "far", seconds: 0.7 }),
  Object.freeze({ id: "center", seconds: 0.8 }),
]);

export function clampKiraEyeDegrees(value, limit) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(-Math.abs(limit), Math.min(Math.abs(limit), number));
}

export function kiraEyeDirectionTarget(direction = "center") {
  const name = String(direction || "center").trim().toLowerCase();
  const targets = {
    center: { yaw: 0, pitch: 0, convergence: 0 },
    // R7-v3 exports Blender local X as Three.js local X, so negative is
    // screen-left and positive is screen-right in the reviewed frontal view.
    left: { yaw: -13, pitch: 0, convergence: 0 },
    right: { yaw: 13, pitch: 0, convergence: 0 },
    up: { yaw: 0, pitch: 7, convergence: 0 },
    down: { yaw: 0, pitch: -7, convergence: 0 },
    near: { yaw: 0, pitch: -1, convergence: 2 },
    far: { yaw: 0, pitch: 0, convergence: 0 },
  };
  const selected = targets[name] || targets.center;
  return Object.freeze({
    id: targets[name] ? name : "center",
    yaw: clampKiraEyeDegrees(selected.yaw, KIRA_EYE_CONTROL_LIMITS_DEGREES.yaw),
    pitch: clampKiraEyeDegrees(selected.pitch, KIRA_EYE_CONTROL_LIMITS_DEGREES.pitch),
    convergence: clampKiraEyeDegrees(selected.convergence, KIRA_EYE_CONTROL_LIMITS_DEGREES.convergence),
  });
}

export function kiraEyeSideTargets(direction = "center") {
  const target = kiraEyeDirectionTarget(direction);
  return Object.freeze({
    id: target.id,
    left: Object.freeze({
      yaw: clampKiraEyeDegrees(target.yaw + target.convergence, KIRA_EYE_CONTROL_LIMITS_DEGREES.yaw),
      pitch: target.pitch,
    }),
    right: Object.freeze({
      yaw: clampKiraEyeDegrees(target.yaw - target.convergence, KIRA_EYE_CONTROL_LIMITS_DEGREES.yaw),
      pitch: target.pitch,
    }),
  });
}

export function kiraEyeBlinkTargets(side = "both", amount = 1) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(Number(amount)) ? Number(amount) : 0));
  const name = String(side || "both").trim().toLowerCase();
  return Object.freeze({
    left: name === "right" ? 0 : clamped,
    right: name === "left" ? 0 : clamped,
  });
}

export function kiraEyeBlinkEnvelope(localAge, duration = 0.7) {
  const safeDuration = Math.max(0.08, Number(duration) || 0.7);
  const normalized = Math.max(0, Math.min(1, Number(localAge) / safeDuration));
  if (normalized <= 0.2) return normalized / 0.2;
  if (normalized <= 0.48) return 1;
  return Math.max(0, 1 - (normalized - 0.48) / 0.52);
}

export function kiraEyeExamPhaseAt(ageSeconds, phases = KIRA_EYE_CONTROL_PHASES) {
  let cursor = Math.max(0, Number(ageSeconds) || 0);
  for (let index = 0; index < phases.length; index += 1) {
    const phase = phases[index];
    if (cursor <= phase.seconds) {
      return Object.freeze({
        ...phase,
        index,
        localAge: cursor,
        complete: false,
      });
    }
    cursor -= phase.seconds;
  }
  return Object.freeze({
    id: "center",
    index: phases.length,
    localAge: 0,
    seconds: 0,
    complete: true,
  });
}

export function buildKiraEyeStructuralReport(context = {}) {
  const requiredNames = [
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
  const foundNames = new Set(context.foundNames || []);
  const missingNames = requiredNames.filter((name) => !foundNames.has(name));
  return Object.freeze({
    version: KIRA_EYE_CONTROL_EXAM_VERSION,
    requiredNames,
    missingNames,
    complete: missingNames.length === 0,
    blinkMorphs: context.blinkMorphs || {},
    headBound: !!context.headBound,
    headBoneName: context.headBoneName || null,
    oldProceduralNodeCount: Number(context.oldProceduralNodeCount || 0),
    gazeMethod: "fixed_socket_and_cornea_bounded_iris_surface_translation",
    blinkSupported: false,
    blinkReason: "R7-v3 does not contain visually approved eyelid geometry; no fake eyelids are generated.",
  });
}
