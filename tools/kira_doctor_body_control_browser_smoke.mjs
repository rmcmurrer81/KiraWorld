import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PREVIEW_ROOT = path.join(
  ROOT,
  "Data",
  "world_builds",
  "notebook_worlds",
  "home_world",
  "builds",
  "home_world_main_house_20260630_223000",
  "preview",
);
const MODEL_PATH = path.join(ROOT, "Avatar", "models", "temp_ai", "kira", "avatar.glb");
const REPORT_ROOT = path.join(ROOT, "Data", "world_tests", "kira_doctor_body_control_20260718");
const REPORT_JSON = path.join(REPORT_ROOT, "kira_doctor_body_control_browser_smoke.json");
const REPORT_MD = path.join(REPORT_ROOT, "kira_doctor_body_control_browser_smoke.md");

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
}

async function waitForHttp(url, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.status < 500) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`Timed out waiting for ${url}: ${lastError?.message || "unknown error"}`);
}

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".glb") return "model/gltf-binary";
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  return "application/octet-stream";
}

function startAssetServer(port) {
  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url || "/", "http://127.0.0.1").pathname);
    const relative = pathname.replace(/^\/+/, "");
    const resolved = path.resolve(ROOT, relative);
    if (!resolved.startsWith(`${ROOT}${path.sep}`) || !fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) {
      response.writeHead(404, { "Access-Control-Allow-Origin": "*" });
      response.end("not found");
      return;
    }
    response.writeHead(200, {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
      "Content-Type": contentType(resolved),
      "Content-Length": fs.statSync(resolved).size,
    });
    fs.createReadStream(resolved).pipe(response);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

function positionDelta(a, b) {
  if (!a || !b) return null;
  return Number(Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z).toFixed(9));
}

function flattenJointSample(sample) {
  const result = {};
  for (const [joint, rotation] of Object.entries(sample?.joints || {})) {
    if (!rotation) continue;
    for (const axis of ["x", "y", "z"]) result[`${joint}.${axis}`] = Number(rotation[axis] || 0);
  }
  return result;
}

function rotationChanges(samples) {
  const flattened = samples.map(flattenJointSample);
  const keys = [...new Set(flattened.flatMap((row) => Object.keys(row)))];
  const changes = [];
  for (const key of keys) {
    const values = flattened.map((row) => row[key]).filter(Number.isFinite);
    const range = values.length ? Math.max(...values) - Math.min(...values) : 0;
    if (range > 0) changes.push({ joint_axis: key, range_radians: Number(range.toFixed(9)) });
  }
  return changes.sort((a, b) => b.range_radians - a.range_radians);
}

function namedJointMotion(samples, jointNames) {
  const evidence = {};
  for (const joint of jointNames) {
    const axisRanges = {};
    let presentSamples = 0;
    for (const axis of ["x", "y", "z"]) {
      const values = samples
        .map((sample) => sample?.joints?.[joint]?.[axis])
        .filter(Number.isFinite);
      presentSamples = Math.max(presentSamples, values.length);
      const range = values.length ? Math.max(...values) - Math.min(...values) : 0;
      axisRanges[axis] = Number(range.toFixed(9));
    }
    const maxRange = Math.max(...Object.values(axisRanges));
    evidence[joint] = {
      present_samples: presentSamples,
      axis_ranges_radians: axisRanges,
      max_range_radians: Number(maxRange.toFixed(9)),
      changed: maxRange > 0,
    };
  }
  return evidence;
}

function everyNamedJointChanged(evidence, jointNames) {
  return jointNames.every((joint) => evidence?.[joint]?.changed === true);
}

function boundMinY(bound) {
  if (!bound || !Number.isFinite(bound.y) || !Number.isFinite(bound.sy)) return null;
  return Number((bound.y - bound.sy / 2).toFixed(6));
}

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function markdown(report) {
  const exam = report.doctor_joint_probe;
  const idle = report.comfort_idle;
  const ground = report.ground_lie;
  return [
    "# Kira doctor body-control isolated browser smoke",
    "",
    `Generated: ${report.generated_at}`,
    "",
    "This loaded Kira's current runtime GLB into a temporary Home World browser page. It did not activate Kira's mind or life loop, write shell state, or persist a body position. The test-station placement happened only inside the disposable browser page before the ground-lie measurement.",
    "",
    "## Results",
    "",
    `- Runtime model loaded: **${report.model.runtime_loaded ? "yes" : "no"}** (${report.model.node_count_sampled} named nodes sampled).`,
    `- Joint exam: **${exam.status}**; ${exam.summary.passed}/${exam.summary.total} phases passed measured quaternion-delta checks.`,
    `- Comfort idle: **${idle.passed ? "passed" : "failed"}**; ${idle.changed_joint_axes} sampled joint axes changed while root displacement was ${idle.max_root_displacement_meters} m.`,
    `- Talking comfort: **${report.comfort_talking.passed ? "passed" : "failed"}**; ${report.comfort_talking.changed_joint_axes} sampled joint axes changed while root displacement was ${report.comfort_talking.max_root_displacement_meters} m.`,
    `- Named comfort assertions: idle arms ${idle.arm_segments_passed ? "passed" : "failed"}, idle representative fingers ${idle.representative_fingers_passed ? "passed" : "failed"}; talking arms ${report.comfort_talking.arm_segments_passed ? "passed" : "failed"}, talking representative fingers ${report.comfort_talking.representative_fingers_passed ? "passed" : "failed"}.`,
    `- Walk/jog/run: **${report.locomotion.every((item) => item.passed) ? "passed" : "failed"}**; measured displacements were ${report.locomotion.map((item) => `${item.gait} ${item.body_displacement_meters} m`).join(", ")}.`,
    `- Ground lie: **${ground.passed ? "passed" : "failed"}**; clearance accepted ${ground.clearance?.sampleCount ?? 0} samples with ${ground.clearance?.blockedSamples ?? "unknown"} blocked, and body displacement was ${ground.body_displacement_meters} m.`,
    `- Ground-lie mesh minimum Y: ${ground.rendered_body_bounds?.min_y ?? "unavailable"} m versus desired ${ground.rendered_body_bounds?.desired_min_y ?? "unavailable"} m; measured rootYOffset ${ground.rendered_body_bounds?.current_root_y_offset ?? "unavailable"}, proposed ${ground.rendered_body_bounds?.proposed_root_y_offset ?? "unavailable"}.`,
    `- Disposable person-owned shell intent: **${report.person_owned_intent_shell_path?.passed ? "passed" : "failed"}**; requested ${report.person_owned_intent_shell_path?.requested_action || "unknown"} and observed ${report.person_owned_intent_shell_path?.observed_action || "unknown"}.`,
    `- Browser/runtime errors: ${report.diagnostics.page_errors.length + report.diagnostics.console_errors.length}.`,
    "",
    "## Visual limitation",
    "",
    report.visual_review.statement,
    "",
    "The skeleton-delta checks prove that the runtime can address these joints. They do not prove that every pose is anatomically natural, comfortable, or ready for unattended use.",
    "",
    "## Artifacts",
    "",
    ...Object.entries(report.artifacts).map(([name, value]) => `- ${name}: \`${value}\``),
    "",
  ].join("\n");
}

if (!fs.existsSync(MODEL_PATH)) throw new Error(`Missing Kira model: ${MODEL_PATH}`);
fs.mkdirSync(REPORT_ROOT, { recursive: true });

const vitePort = await freePort();
const assetPort = await freePort();
const worldUrl = `http://127.0.0.1:${vitePort}/?area=home&doctorBodySmoke=20260718`;
const modelUrl = `http://127.0.0.1:${assetPort}/Avatar/models/temp_ai/kira/avatar.glb?v=${fs.statSync(MODEL_PATH).mtimeMs}`;
const viteEntry = path.join(PREVIEW_ROOT, "node_modules", "vite", "bin", "vite.js");
const vite = spawn(process.execPath, [viteEntry, "--host", "127.0.0.1", "--port", String(vitePort), "--strictPort"], {
  cwd: PREVIEW_ROOT,
  windowsHide: true,
  stdio: ["ignore", "pipe", "pipe"],
});
let viteOutput = "";
vite.stdout.on("data", (chunk) => { viteOutput = `${viteOutput}${chunk}`.slice(-12_000); });
vite.stderr.on("data", (chunk) => { viteOutput = `${viteOutput}${chunk}`.slice(-12_000); });

let assetServer = null;
let browser = null;
const diagnostics = { page_errors: [], console_errors: [], request_failures: [], http_errors: [] };

try {
  assetServer = await startAssetServer(assetPort);
  await waitForHttp(worldUrl);
  browser = await chromium.launch({
    headless: true,
    args: ["--use-angle=default", "--enable-webgl", "--ignore-gpu-blocklist"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.on("pageerror", (error) => diagnostics.page_errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.console_errors.push(message.text());
  });
  page.on("requestfailed", (request) => diagnostics.request_failures.push({
    url: request.url(),
    error: request.failure()?.errorText || "failed",
  }));
  page.on("response", (response) => {
    if (response.status() >= 400) diagnostics.http_errors.push({ status: response.status(), url: response.url() });
  });

  await page.goto(worldUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.injectShellState), null, { timeout: 120_000 });
  await page.evaluate((url) => {
    window.kiraHomeWorldDebug.injectShellState({
      active_candidate: "kira",
      active_label: "Kira",
      active_ai: "Kira",
      active_form: "civilian",
      active_action: "idle",
      active_model_url: url,
      active_pose_manifest_url: "",
      location: "home",
      isolated_browser_test: true,
    });
  }, modelUrl);
  await page.waitForFunction(
    () => Boolean(window.kiraHomeWorldDebug?.activeAvatarState?.().rootPresent)
      && Boolean(window.kiraHomeWorldDebug?.activeAvatarState?.().proceduralRig?.usable),
    null,
    { timeout: 120_000 },
  );
  // Let independently loaded room props settle before the two visual aids so
  // their appearance is not mistaken for avatar motion.
  await page.waitForTimeout(3_500);

  const loadedState = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const nodeNames = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarModelNodeNames());
  const doctorProbe = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraDoctorJointControl());

  await page.evaluate(() => window.kiraHomeWorldDebug.focusActiveAvatar({ x: 2.8, y: 1.55, z: 4.1 }));
  const idleScreenshot1 = path.join(REPORT_ROOT, "comfort_idle_t1.png");
  const idleScreenshot2 = path.join(REPORT_ROOT, "comfort_idle_t2.png");
  await page.screenshot({ path: idleScreenshot1 });
  const idleSamples = [];
  for (let index = 0; index < 5; index += 1) {
    idleSamples.push(await page.evaluate(() => window.kiraHomeWorldDebug.kiraComfortIdleStatus()));
    if (index < 4) await page.waitForTimeout(650);
  }
  await page.screenshot({ path: idleScreenshot2 });
  const idlePosition = idleSamples[0]?.bodyPosition || null;
  const idleDisplacements = idleSamples.map((sample) => positionDelta(idlePosition, sample?.bodyPosition));
  const idleRotationChanges = rotationChanges(idleSamples);
  const armJointNames = ["leftUpperArm", "leftForearm", "rightUpperArm", "rightForearm"];
  const fingerJointNames = [
    "leftThumb", "leftIndex", "leftMiddle", "leftRing", "leftPinky",
    "rightThumb", "rightIndex", "rightMiddle", "rightRing", "rightPinky",
  ];
  const representativeFingerNames = ["leftIndex", "rightIndex"];
  const idleArmMotion = namedJointMotion(idleSamples, armJointNames);
  const idleFingerMotion = namedJointMotion(idleSamples, fingerJointNames);

  const talkingShellState = {
    active_candidate: "kira",
    active_label: "Kira",
    active_ai: "Kira",
    active_form: "civilian",
    active_action: "talking",
    active_model_url: modelUrl,
    active_pose_manifest_url: "",
    location: "home",
    isolated_browser_test: true,
  };
  await page.evaluate((state) => window.kiraHomeWorldDebug.injectShellState(state), talkingShellState);
  await page.waitForTimeout(150);
  const talkingSamples = [];
  for (let index = 0; index < 5; index += 1) {
    talkingSamples.push(await page.evaluate(() => window.kiraHomeWorldDebug.kiraComfortIdleStatus()));
    if (index < 4) await page.waitForTimeout(450);
  }
  const talkingScreenshot = path.join(REPORT_ROOT, "comfort_talking.png");
  await page.screenshot({ path: talkingScreenshot });
  const talkingPosition = talkingSamples[0]?.bodyPosition || null;
  const talkingDisplacements = talkingSamples.map((sample) => positionDelta(talkingPosition, sample?.bodyPosition));
  const talkingRotationChanges = rotationChanges(talkingSamples);
  const talkingArmMotion = namedJointMotion(talkingSamples, armJointNames);
  const talkingFingerMotion = namedJointMotion(talkingSamples, fingerJointNames);
  const maxTalkingDisplacement = Math.max(...talkingDisplacements.filter(Number.isFinite), 0);
  const talkingArmSegmentsPassed = everyNamedJointChanged(talkingArmMotion, armJointNames);
  const talkingRepresentativeFingersPassed = everyNamedJointChanged(talkingFingerMotion, representativeFingerNames);
  const talkingPassed = talkingRotationChanges.length >= 4
    && talkingArmSegmentsPassed
    && talkingRepresentativeFingersPassed
    && maxTalkingDisplacement === 0
    && talkingSamples.some((sample) => Math.abs(Number(sample?.offsets?.gesture || 0)) > 0.01);

  await page.evaluate((state) => window.kiraHomeWorldDebug.injectShellState(state), {
    ...talkingShellState,
    active_action: "idle",
  });
  await page.waitForTimeout(200);

  const locomotion = [];
  for (const spec of [
    { gait: "walk", method: "startWalkPractice", seconds: 2.6 },
    { gait: "jog", method: "startJogPractice", seconds: 2.3 },
    { gait: "run", method: "startRunPractice", seconds: 2.0 },
  ]) {
    await page.evaluate(() => window.kiraHomeWorldDebug.setActiveAvatarPosition({
      x: -1.1,
      y: 0.05,
      z: 11.8,
      roamZone: "kira_home_world",
    }));
    await page.waitForTimeout(120);
    const before = await page.evaluate(() => window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("locomotion_before"));
    const started = await page.evaluate((method) => window.kiraHomeWorldDebug[method](), spec.method);
    await page.waitForTimeout(spec.seconds * 1000);
    const after = await page.evaluate(() => window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("locomotion_after"));
    const activeState = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
    const displacement = positionDelta(before?.activePosition, after?.activePosition);
    const transition = after?.transitionEvidence || null;
    locomotion.push({
      gait: spec.gait,
      started,
      sample_seconds: spec.seconds,
      body_position_before: before?.activePosition || null,
      body_position_after: after?.activePosition || null,
      body_displacement_meters: displacement,
      runtime_action: after?.action || null,
      runtime_gait_mode: activeState?.gaitMode || null,
      moving: Boolean(activeState?.moving),
      teleported: transition?.teleported ?? null,
      transition_distance_meters: transition?.distanceMeters ?? null,
      transition_path_sample_count: transition?.pathSampleCount ?? null,
      collision_blocked: transition?.collisionBlocked ?? null,
      passed: started === true
        && displacement > 0.05
        && after?.action === spec.gait
        && activeState?.gaitMode === spec.gait
        && transition?.teleported === false,
      note: "The disposable test-station placement is setup. The measured route starts from the body's actual station position and transitionEvidence must report teleported=false.",
    });
  }

  // Put the disposable preview body at a known, broad supported front-yard test station.
  // This is setup only; the measured lie action must not change the body position.
  await page.evaluate(() => window.kiraHomeWorldDebug.setActiveAvatarPosition({
    x: -1.1,
    y: 0.05,
    z: 11.8,
    roamZone: "kira_home_world",
  }));
  await page.waitForTimeout(250);
  const beforeGround = await page.evaluate(() => window.kiraHomeWorldDebug.kiraComfortIdleStatus());
  const beforeGroundVisualBounds = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarVisualBounds());
  const groundStarted = await page.evaluate(() => window.kiraHomeWorldDebug.startLieOnCurrentGround({ seconds: 8 }));
  await page.waitForTimeout(850);
  const groundState = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const afterGround = await page.evaluate(() => window.kiraHomeWorldDebug.kiraComfortIdleStatus());
  const afterGroundVisualBounds = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarVisualBounds());
  const groundEvidence = await page.evaluate(() => window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("ground_lie_bounds"));
  const groundBounds = await page.evaluate(() => ({
    sketchfabModel: window.kiraHomeWorldDebug.objectBounds("Sketchfab_model"),
    objectMeshes: window.kiraHomeWorldDebug.objectBounds("Object_"),
  }));
  await page.evaluate(() => window.kiraHomeWorldDebug.focusActiveAvatar({ x: 3.2, y: 1.7, z: 4.5 }));
  const groundScreenshot = path.join(REPORT_ROOT, "ground_lie.png");
  await page.screenshot({ path: groundScreenshot });

  const examPassed = doctorProbe?.status === "pass"
    && doctorProbe?.summary?.passed === doctorProbe?.summary?.total
    && doctorProbe?.summary?.failed === 0;
  const maxIdleDisplacement = Math.max(...idleDisplacements.filter(Number.isFinite), 0);
  const idleArmSegmentsPassed = everyNamedJointChanged(idleArmMotion, armJointNames);
  const idleRepresentativeFingersPassed = everyNamedJointChanged(idleFingerMotion, representativeFingerNames);
  const idlePassed = idleRotationChanges.length >= 4
    && idleArmSegmentsPassed
    && idleRepresentativeFingersPassed
    && maxIdleDisplacement === 0;
  const groundDisplacement = positionDelta(beforeGround?.bodyPosition, afterGround?.bodyPosition);
  const fallbackBodyBound = groundBounds.sketchfabModel.find((item) => item.name === "Sketchfab_model")
    || groundBounds.sketchfabModel[0]
    || groundBounds.objectMeshes
      .filter((item) => Number(item.sy) > 0.8)
      .sort((a, b) => Number(b.sy) - Number(a.sy))[0]
    || null;
  const renderedMinY = Number(afterGroundVisualBounds?.min?.y ?? boundMinY(fallbackBodyBound));
  const supportY = Number(afterGroundVisualBounds?.supportY ?? groundEvidence?.supportState?.y ?? beforeGround?.bodyPosition?.y ?? 0.05);
  const desiredMinY = Number((supportY + 0.008).toFixed(6));
  const currentRootYOffset = Number(groundEvidence?.postureState?.rootYOffset ?? 0.094);
  const proposedRootYOffset = Number.isFinite(renderedMinY)
    ? Number((currentRootYOffset + desiredMinY - renderedMinY).toFixed(4))
    : null;
  const groundMechanicalPassed = groundStarted === true
    && groundState?.groundLieClearance?.sampleCount === 15
    && groundState?.groundLieClearance?.blockedSamples === 0
    && groundDisplacement === 0
    && groundState?.doctorBodyExam?.running !== true;
  const groundNoPenetration = Number.isFinite(renderedMinY) && renderedMinY >= supportY;
  const groundContactPassed = Number.isFinite(renderedMinY)
    && Math.abs(renderedMinY - desiredMinY) <= 0.006;
  const groundPassed = groundMechanicalPassed && groundNoPenetration && groundContactPassed;

  // Exercise the ordinary same-avatar shell-state apply path using a disposable
  // person-owned intent revision. This happens last so the live timed exam cannot
  // interfere with the direct probe, comfort, locomotion, or ground measurements.
  const beforePersonOwnedIntent = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const disposableIntentRevision = `isolated-browser-doctor-exam-${Date.now()}`;
  const personOwnedIntentApplyResult = await page.evaluate(({ state, revision }) => (
    window.kiraHomeWorldDebug.injectShellState({
      ...state,
      active_action: "doctor_body_exam",
      active_intent_updated_at: revision,
      active_intent_source: "isolated_browser_person_owned_intent_smoke",
      active_intent_metadata: { person_owned_intent: true, isolated_browser_test: true },
    })
  ), { state: talkingShellState, revision: disposableIntentRevision });
  await page.waitForTimeout(180);
  const afterPersonOwnedIntent = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const personOwnedIntentRootDisplacement = positionDelta(
    beforePersonOwnedIntent?.position,
    afterPersonOwnedIntent?.position,
  );
  const personOwnedIntentPassed = afterPersonOwnedIntent?.doctorBodyExam?.running === true
    && afterPersonOwnedIntent?.action === "doctor_body_control_exam"
    && personOwnedIntentRootDisplacement === 0;

  const artifacts = {
    report_json: path.relative(ROOT, REPORT_JSON).replaceAll("\\", "/"),
    report_markdown: path.relative(ROOT, REPORT_MD).replaceAll("\\", "/"),
    idle_screenshot_t1: path.relative(ROOT, idleScreenshot1).replaceAll("\\", "/"),
    idle_screenshot_t2: path.relative(ROOT, idleScreenshot2).replaceAll("\\", "/"),
    talking_screenshot: path.relative(ROOT, talkingScreenshot).replaceAll("\\", "/"),
    ground_lie_screenshot: path.relative(ROOT, groundScreenshot).replaceAll("\\", "/"),
  };
  const report = {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    status: examPassed
      && idlePassed
      && talkingPassed
      && locomotion.every((item) => item.passed)
      && groundPassed
      && personOwnedIntentPassed
      ? "control_checks_passed_visual_naturalness_not_passed"
      : "failed_or_incomplete",
    isolation: {
      live_person_activated: false,
      life_loop_started: false,
      live_shell_written: false,
      saved_body_position_written: false,
      disposable_preview_shell_state_injected: true,
      disposable_test_station_placement: { x: -1.1, y: 0.05, z: 11.8 },
    },
    model: {
      path: path.relative(ROOT, MODEL_PATH).replaceAll("\\", "/"),
      sha256: sha256(MODEL_PATH),
      runtime_loaded: Boolean(loadedState?.rootPresent),
      procedural_rig_usable: Boolean(loadedState?.proceduralRig?.usable),
      node_count_sampled: nodeNames.length,
      named_nodes: nodeNames,
    },
    doctor_joint_probe: {
      passed: examPassed,
      status: doctorProbe?.status || "missing",
      summary: doctorProbe?.summary || null,
      result_count: doctorProbe?.results?.length || 0,
      results: doctorProbe?.results || [],
      visually_reviewed: false,
      limitation: doctorProbe?.limitation || null,
    },
    comfort_idle: {
      passed: idlePassed,
      sample_count: idleSamples.length,
      sample_interval_seconds: 0.65,
      changed_joint_axes: idleRotationChanges.length,
      max_root_displacement_meters: maxIdleDisplacement,
      root_positions: idleSamples.map((sample) => sample?.bodyPosition || null),
      root_translation_requests: idleSamples.map((sample) => sample?.rootTranslationRequested || null),
      arm_segments_passed: idleArmSegmentsPassed,
      representative_fingers: representativeFingerNames,
      representative_fingers_passed: idleRepresentativeFingersPassed,
      named_arm_motion: idleArmMotion,
      named_finger_motion: idleFingerMotion,
      individual_finger_joints_changed: fingerJointNames.filter((joint) => idleFingerMotion[joint]?.changed),
      top_rotation_ranges: idleRotationChanges.slice(0, 20),
      samples: idleSamples,
    },
    comfort_talking: {
      passed: talkingPassed,
      sample_count: talkingSamples.length,
      sample_interval_seconds: 0.45,
      changed_joint_axes: talkingRotationChanges.length,
      max_root_displacement_meters: maxTalkingDisplacement,
      root_positions: talkingSamples.map((sample) => sample?.bodyPosition || null),
      root_translation_requests: talkingSamples.map((sample) => sample?.rootTranslationRequested || null),
      arm_segments_passed: talkingArmSegmentsPassed,
      representative_fingers: representativeFingerNames,
      representative_fingers_passed: talkingRepresentativeFingersPassed,
      named_arm_motion: talkingArmMotion,
      named_finger_motion: talkingFingerMotion,
      individual_finger_joints_changed: fingerJointNames.filter((joint) => talkingFingerMotion[joint]?.changed),
      top_rotation_ranges: talkingRotationChanges.slice(0, 20),
      samples: talkingSamples,
    },
    locomotion,
    posture_actions_not_tested: [
      { action: "sit_couch", status: "not_executed", reason: "This smoke did not wait for a complete truthful route to the couch." },
      { action: "lie_couch", status: "not_executed", reason: "This smoke did not wait for a complete truthful route and visual contact review." },
      { action: "lie_bed", status: "not_executed", reason: "This smoke did not wait for a complete truthful route and visual contact review." },
    ],
    ground_lie: {
      passed: groundPassed,
      mechanical_passed: groundMechanicalPassed,
      rendered_contact_passed: groundContactPassed,
      no_mesh_penetration: groundNoPenetration,
      rendered_contact_tolerance_meters: 0.006,
      started: groundStarted,
      clearance: groundState?.groundLieClearance || null,
      action_after_850ms: groundState?.action || null,
      skill_interaction: groundState?.skillInteraction || null,
      posture_state_visible_in_active_state: Boolean(groundState?.skillInteraction),
      body_position_before: beforeGround?.bodyPosition || null,
      body_position_after: afterGround?.bodyPosition || null,
      body_displacement_meters: groundDisplacement,
      rendered_body_bounds: {
        exact_active_avatar_before: beforeGroundVisualBounds,
        exact_active_avatar_after: afterGroundVisualBounds,
        fallback_scene_bound: fallbackBodyBound,
        min_y: renderedMinY,
        support_y: supportY,
        desired_min_y: desiredMinY,
        gap_above_desired_meters: Number.isFinite(renderedMinY) ? Number((renderedMinY - desiredMinY).toFixed(6)) : null,
        current_root_y_offset: currentRootYOffset,
        proposed_root_y_offset: proposedRootYOffset,
        proposal_status: groundContactPassed
          ? "current_offset_within_contact_tolerance_optional_exact_clearance_refinement_only"
          : Number.isFinite(proposedRootYOffset)
            ? "measurement_only_not_applied_pending_owner_review"
          : "not_computable",
        method: "mesh-only THREE.Box3 for activeAvatarRoot exposed by activeAvatarVisualBounds after the posture rendered",
      },
      all_candidate_bounds: groundBounds,
      note: "The debug position setter established only the isolated test station. The measured lie action itself had to remain at that exact position.",
    },
    person_owned_intent_shell_path: {
      passed: personOwnedIntentPassed,
      live_shell_written: false,
      persisted_position_written: false,
      requested_action: "doctor_body_exam",
      requested_revision: disposableIntentRevision,
      requested_metadata: { person_owned_intent: true, isolated_browser_test: true },
      apply_result: personOwnedIntentApplyResult,
      state_before: beforePersonOwnedIntent,
      state_after: afterPersonOwnedIntent,
      observed_action: afterPersonOwnedIntent?.action || null,
      observed_exam: afterPersonOwnedIntent?.doctorBodyExam || null,
      root_displacement_meters: personOwnedIntentRootDisplacement,
      method: "same-avatar disposable shell revision through kiraHomeWorldDebug.injectShellState -> setActiveMarker -> maybeStartBodyPracticeFromShellAction",
    },
    visual_review: {
      performed_by_script: false,
      comfort_idle_visually_natural: false,
      talking_comfort_visually_natural: false,
      ground_lie_visually_natural: false,
      statement: "Codex inspected the same-build stills at an ordinary follow-camera distance. The comfort-idle difference is too subtle to distinguish reliably in the still images, and the standing/talking body still reads somewhat stiff. The corrected ground-lie frame now agrees with the measured contact tolerance, but the arms, legs, and overall resting pose still look stiff rather than naturally settled. The time-series joint measurements are runtime-control evidence, not visual-naturalness evidence.",
    },
    diagnostics,
    artifacts,
    vite_output_tail: viteOutput,
  };
  fs.writeFileSync(REPORT_JSON, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  fs.writeFileSync(REPORT_MD, `${markdown(report)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({
    status: report.status,
    exam: report.doctor_joint_probe.summary,
    comfort_idle: {
      changed_joint_axes: report.comfort_idle.changed_joint_axes,
      max_root_displacement_meters: report.comfort_idle.max_root_displacement_meters,
      arm_segments_passed: report.comfort_idle.arm_segments_passed,
      representative_fingers_passed: report.comfort_idle.representative_fingers_passed,
      individual_finger_joints_changed: report.comfort_idle.individual_finger_joints_changed,
    },
    comfort_talking: {
      changed_joint_axes: report.comfort_talking.changed_joint_axes,
      max_root_displacement_meters: report.comfort_talking.max_root_displacement_meters,
      arm_segments_passed: report.comfort_talking.arm_segments_passed,
      representative_fingers_passed: report.comfort_talking.representative_fingers_passed,
      individual_finger_joints_changed: report.comfort_talking.individual_finger_joints_changed,
    },
    locomotion: report.locomotion,
    ground_lie: report.ground_lie,
    person_owned_intent_shell_path: report.person_owned_intent_shell_path,
    diagnostics,
    artifacts,
  }, null, 2)}\n`);
} finally {
  if (browser) await browser.close();
  if (assetServer) await new Promise((resolve) => assetServer.close(resolve));
  if (!vite.killed) vite.kill();
  await new Promise((resolve) => {
    const timer = setTimeout(resolve, 3_000);
    vite.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}
