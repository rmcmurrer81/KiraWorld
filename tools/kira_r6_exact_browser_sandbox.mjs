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
  "Data", "world_builds", "notebook_worlds", "home_world", "builds",
  "home_world_main_house_20260630_223000", "preview",
);
const R6_PATH = path.join(
  ROOT, "Avatar", "avatar_builder", "candidate_sources", "kira_provisional_body_r6",
  "r6_20260718_163658", "kira_provisional_body_r6.glb",
);
const LIVE_BODY_PATH = path.join(ROOT, "Avatar", "models", "temp_ai", "kira", "avatar.glb");
const STAGED_EYE_PATH = path.join(
  ROOT, "Avatar", "models", "staged", "kira", "eyes", "kira_brown_eye_rig_v3_2",
  "kira_brown_eye_rig_v3_2.glb",
);
const PUBLIC_EYE_PATH = path.join(
  PREVIEW_ROOT, "public", "models", "home_world", "kira", "kira_brown_eye_rig_v3_2.glb",
);
const SELECTION_PATH = path.join(ROOT, "Avatar", "state", "body_selections", "kira_runtime_body_selection.json");
const SHELL_STATE_PATH = path.join(ROOT, "Data", "runtime", "kira_world_shell_state.json");
const PREVIEW_MAIN_PATH = path.join(PREVIEW_ROOT, "src", "main.js");
const MOUTH_CONTROLLER_PATH = path.join(PREVIEW_ROOT, "src", "existing_mouth_lipsync.js");
const SERVER_MAIN_PATH = path.join(ROOT, "server", "main.js");
const REPORT_PARENT = path.join(ROOT, "Data", "world_tests", "kira_r6_exact_browser_sandbox_20260718");

const EXPECTED_R6_SHA256 = "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77";
const EXPECTED_EYE_SHA256 = "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413";

function runId() {
  return new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function relative(filePath) {
  return path.relative(ROOT, filePath).replaceAll("\\", "/");
}

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function fileSnapshot(filePath) {
  if (!fs.existsSync(filePath)) return { path: relative(filePath), exists: false, sha256: null, bytes: null };
  const stat = fs.statSync(filePath);
  return {
    path: relative(filePath),
    exists: true,
    sha256: sha256(filePath),
    bytes: stat.size,
  };
}

function shellSnapshot() {
  const snapshot = fileSnapshot(SHELL_STATE_PATH);
  if (!snapshot.exists) return { ...snapshot, active_candidate: null, active_conversation_mode: null };
  try {
    const state = JSON.parse(fs.readFileSync(SHELL_STATE_PATH, "utf8"));
    return {
      ...snapshot,
      active_candidate: String(state.active_candidate || ""),
      active_conversation_mode: String(state.active_conversation_mode || ""),
      updated_at: state.updated_at || null,
    };
  } catch (error) {
    return { ...snapshot, parse_error: error.message, active_candidate: null, active_conversation_mode: null };
  }
}

function guardSnapshots() {
  return {
    r6_candidate: fileSnapshot(R6_PATH),
    live_body: fileSnapshot(LIVE_BODY_PATH),
    staged_eye: fileSnapshot(STAGED_EYE_PATH),
    public_eye: fileSnapshot(PUBLIC_EYE_PATH),
    runtime_selection: fileSnapshot(SELECTION_PATH),
    live_shell: shellSnapshot(),
    preview_main: fileSnapshot(PREVIEW_MAIN_PATH),
    existing_mouth_controller: fileSnapshot(MOUTH_CONTROLLER_PATH),
    server_main: fileSnapshot(SERVER_MAIN_PATH),
  };
}

function unchanged(before, after, key) {
  return before[key]?.exists === after[key]?.exists && before[key]?.sha256 === after[key]?.sha256;
}

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

function startAssetServer(port) {
  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url || "/", "http://127.0.0.1").pathname);
    const relativePath = pathname.replace(/^\/+/, "");
    const resolved = path.resolve(ROOT, relativePath);
    const allowed = resolved.startsWith(`${ROOT}${path.sep}`)
      && fs.existsSync(resolved)
      && fs.statSync(resolved).isFile();
    if (!allowed) {
      response.writeHead(404, { "Access-Control-Allow-Origin": "*" });
      response.end("not found");
      return;
    }
    response.writeHead(200, {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
      "Content-Type": path.extname(resolved).toLowerCase() === ".glb"
        ? "model/gltf-binary"
        : "application/octet-stream",
      "Content-Length": fs.statSync(resolved).size,
    });
    fs.createReadStream(resolved).pipe(response);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

function distance(a, b) {
  if (!a || !b) return null;
  return Number(Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z).toFixed(9));
}

function vectorDelta(a, b) {
  return distance(a, b);
}

function finiteBounds(bounds) {
  if (!bounds) return false;
  const values = [
    bounds.min?.x, bounds.min?.y, bounds.min?.z,
    bounds.max?.x, bounds.max?.y, bounds.max?.z,
    bounds.size?.x, bounds.size?.y, bounds.size?.z,
  ];
  return values.every(Number.isFinite) && bounds.size.y > 0.5;
}

async function addPrivacyCover(page, mode, label) {
  await page.evaluate(({ mode: coverMode, label: coverLabel }) => {
    document.getElementById("r6-private-evidence-cover")?.remove();
    const cover = document.createElement("div");
    cover.id = "r6-private-evidence-cover";
    Object.assign(cover.style, {
      position: "fixed",
      zIndex: "2147483647",
      pointerEvents: "none",
      boxSizing: "border-box",
      color: "#d8f2ff",
      background: "#07131f",
      border: "4px solid #3a9cc8",
      font: "700 18px/1.4 system-ui, sans-serif",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      padding: "24px",
      letterSpacing: "0.02em",
    });
    if (coverMode === "head") {
      Object.assign(cover.style, {
        left: "0",
        bottom: "0",
        width: "calc(100vw - 270px)",
        height: "50vh",
      });
    } else {
      Object.assign(cover.style, {
        left: "0",
        top: "0",
        width: "calc(100vw - 270px)",
        height: "100vh",
      });
    }
    cover.textContent = coverLabel;
    document.body.appendChild(cover);
  }, { mode, label });
}

async function removePrivacyCover(page) {
  await page.evaluate(() => document.getElementById("r6-private-evidence-cover")?.remove());
}

async function coveredScreenshot(page, reportDir, name, mode, label) {
  const filePath = path.join(reportDir, `${name}_covered.png`);
  await addPrivacyCover(page, mode, label);
  await page.screenshot({ path: filePath });
  await removePrivacyCover(page);
  return {
    path: relative(filePath),
    sha256: sha256(filePath),
    privacy_cover: mode,
  };
}

function errorText(error) {
  return error?.stack || error?.message || String(error);
}

const id = runId();
const reportDir = path.join(REPORT_PARENT, id);
const evidencePath = path.join(reportDir, "evidence.json");
const markdownPath = path.join(reportDir, "report.md");
fs.mkdirSync(reportDir, { recursive: true });

const before = guardSnapshots();
const diagnostics = { page_errors: [], console_errors: [], request_failures: [], http_errors: [] };
const evidence = {
  schema_version: 1,
  generated_at: new Date().toISOString(),
  run_id: id,
  status: "failed_or_incomplete",
  exact_candidate_sha256: EXPECTED_R6_SHA256,
  isolation: {
    live_person_activated: false,
    life_loop_started: false,
    voice_audio_played: false,
    shell_state_persisted: false,
    model_selection_changed: false,
    live_model_changed: false,
    query: "?area=home&r6BrowserSmoke=1&kiraEyeRig=v3.2",
    motion_smoke_query_used: false,
    activation_allowed: false,
    autobuild_allowed: false,
  },
  guards: { before, after: null, unchanged: {} },
  assets: {},
  checks: {},
  body_motion: {},
  eyes: {},
  mouth: {},
  screenshots: {},
  diagnostics,
  limitations: [
    "These are inactive browser compatibility checks, not Kira or owner approval.",
    "Numeric and covered screenshot evidence does not prove visual naturalness.",
    "This run exercises the existing procedural rig; it does not visually approve embedded animation clips.",
    "Adult anatomical completeness is not proven by this runtime check.",
    "Activation and autobuild remain blocked regardless of the technical result.",
  ],
};

let vite = null;
let viteOutput = "";
let assetServer = null;
let browser = null;
let fatalError = null;

try {
  const required = [R6_PATH, LIVE_BODY_PATH, STAGED_EYE_PATH, PUBLIC_EYE_PATH, PREVIEW_MAIN_PATH, MOUTH_CONTROLLER_PATH];
  for (const filePath of required) {
    if (!fs.existsSync(filePath)) throw new Error(`Missing required file: ${filePath}`);
  }
  if (before.r6_candidate.sha256 !== EXPECTED_R6_SHA256) {
    throw new Error(`Exact R6 hash mismatch: ${before.r6_candidate.sha256}`);
  }
  if (before.staged_eye.sha256 !== EXPECTED_EYE_SHA256 || before.public_eye.sha256 !== EXPECTED_EYE_SHA256) {
    throw new Error(`Exact staged/public eye hash mismatch: ${before.staged_eye.sha256} / ${before.public_eye.sha256}`);
  }
  if (before.live_shell.parse_error) throw new Error(`Live shell state is not readable: ${before.live_shell.parse_error}`);
  if (before.live_shell.active_candidate) {
    throw new Error(`Refusing inactive R6 sandbox while live candidate is active: ${before.live_shell.active_candidate}`);
  }

  const vitePort = await freePort();
  const assetPort = await freePort();
  const worldUrl = `http://127.0.0.1:${vitePort}/?area=home&r6BrowserSmoke=1&kiraEyeRig=v3.2`;
  const r6Url = `http://127.0.0.1:${assetPort}/${relative(R6_PATH)}?sha256=${EXPECTED_R6_SHA256}`;
  const viteEntry = path.join(PREVIEW_ROOT, "node_modules", "vite", "bin", "vite.js");
  vite = spawn(process.execPath, [viteEntry, "--host", "127.0.0.1", "--port", String(vitePort), "--strictPort"], {
    cwd: PREVIEW_ROOT,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
  vite.stdout.on("data", (chunk) => { viteOutput = `${viteOutput}${chunk}`.slice(-12_000); });
  vite.stderr.on("data", (chunk) => { viteOutput = `${viteOutput}${chunk}`.slice(-12_000); });
  assetServer = await startAssetServer(assetPort);
  await waitForHttp(worldUrl);

  browser = await chromium.launch({
    headless: true,
    args: ["--use-angle=default", "--enable-webgl", "--ignore-gpu-blocklist"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.addInitScript(() => {
    let seed = 0x7f18c6d2;
    Math.random = () => {
      seed = (1664525 * seed + 1013904223) >>> 0;
      return seed / 0x100000000;
    };
  });
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
  await page.evaluate((modelUrl) => window.kiraHomeWorldDebug.injectShellState({
    active_candidate: "kira",
    active_label: "Kira",
    active_ai: "Kira",
    active_form: "private_inactive_r6_browser_sandbox",
    active_action: "idle",
    active_model_url: modelUrl,
    active_pose_manifest_url: "",
    location: "home",
    isolated_browser_test: true,
    do_not_persist: true,
  }), r6Url);
  await page.waitForFunction((expected) => {
    const debug = window.kiraHomeWorldDebug;
    const state = debug?.activeAvatarState?.();
    return Boolean(state?.rootPresent && String(state.modelUrl || "").includes(expected));
  }, "kira_provisional_body_r6.glb", { timeout: 120_000 });
  await page.waitForFunction(() => {
    const debug = window.kiraHomeWorldDebug;
    const eye = debug?.kiraEyeStatus?.();
    const mouth = debug?.kiraExistingMouthLipSync?.();
    return Boolean(eye?.active && eye?.structural?.complete && eye?.headBound && mouth?.active);
  }, null, { timeout: 120_000 });
  await page.waitForTimeout(900);

  const initial = await page.evaluate(() => ({
    state: window.kiraHomeWorldDebug.activeAvatarState(),
    bounds: window.kiraHomeWorldDebug.activeAvatarVisualBounds(),
    nodes: window.kiraHomeWorldDebug.activeAvatarModelNodeNames(),
    evidence: window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("r6_exact_initial"),
  }));
  evidence.assets = {
    r6_path: relative(R6_PATH),
    r6_sha256: before.r6_candidate.sha256,
    staged_eye_path: relative(STAGED_EYE_PATH),
    staged_eye_sha256: before.staged_eye.sha256,
    public_eye_path: relative(PUBLIC_EYE_PATH),
    public_eye_sha256: before.public_eye.sha256,
    transient_model_url: r6Url,
  };
  evidence.body_motion.initial = initial;

  await page.evaluate(() => window.kiraHomeWorldDebug.setActiveAvatarPosition({
    x: -1.1, y: 0.05, z: 11.8, roamZone: "kira_home_world", waitSeconds: 0,
  }));
  const walkBefore = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const walkStarted = await page.evaluate(() => window.kiraHomeWorldDebug.startWalkPractice());
  const walkSamples = [];
  for (let index = 0; index < 22; index += 1) {
    await page.waitForTimeout(140);
    walkSamples.push(await page.evaluate(() => ({
      state: window.kiraHomeWorldDebug.activeAvatarState(),
      bounds: window.kiraHomeWorldDebug.activeAvatarVisualBounds(),
      observation: window.kiraHomeWorldDebug.observationSample("r6_exact_walk"),
    })));
  }
  const walkAfter = walkSamples.at(-1);
  evidence.body_motion.walk = {
    started: walkStarted,
    before: walkBefore,
    samples: walkSamples,
    displacement_meters: distance(walkBefore.position, walkAfter?.state?.position),
  };
  evidence.screenshots.walk = await coveredScreenshot(
    page, reportDir, "walk", "body",
    "PRIVATE EXACT-R6 BODY HIDDEN — numeric walk/grounding evidence only",
  );

  await page.evaluate(() => window.kiraHomeWorldDebug.setActiveAvatarPosition({
    x: -4.05, y: 0.05, z: 1.82, roamZone: "kira_home_world", waitSeconds: 0,
  }));
  const sitBefore = await page.evaluate(() => ({
    state: window.kiraHomeWorldDebug.activeAvatarState(),
    bounds: window.kiraHomeWorldDebug.activeAvatarVisualBounds(),
  }));
  const sitStarted = await page.evaluate(() => window.kiraHomeWorldDebug.startPostureTest("sit_couch"));
  await page.waitForTimeout(950);
  const sitDuring = await page.evaluate(() => ({
    state: window.kiraHomeWorldDebug.activeAvatarState(),
    bounds: window.kiraHomeWorldDebug.activeAvatarVisualBounds(),
    comfort: window.kiraHomeWorldDebug.kiraComfortIdleStatus(),
    evidence: window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("r6_exact_sit"),
  }));
  evidence.body_motion.sit = { started: sitStarted, before: sitBefore, during: sitDuring };
  evidence.screenshots.sit = await coveredScreenshot(
    page, reportDir, "sit", "body",
    "PRIVATE EXACT-R6 BODY HIDDEN — numeric sit deformation evidence only",
  );

  await page.evaluate(() => window.kiraHomeWorldDebug.setActiveAvatarPosition({
    x: 1.0, y: 0.05, z: 8.36, roamZone: "kira_home_world", waitSeconds: 0,
  }));
  const reachBefore = await page.evaluate(() => ({
    state: window.kiraHomeWorldDebug.activeAvatarState(),
    evidence: window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("r6_exact_reach_before"),
  }));
  const reachStarted = await page.evaluate(() => window.kiraHomeWorldDebug.startFrontDoorReach());
  const reachSamples = [];
  for (let index = 0; index < 18; index += 1) {
    await page.waitForTimeout(140);
    reachSamples.push(await page.evaluate(() => ({
      state: window.kiraHomeWorldDebug.activeAvatarState(),
      bounds: window.kiraHomeWorldDebug.activeAvatarVisualBounds(),
      evidence: window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("r6_exact_turn_reach"),
    })));
  }
  const reachAfter = await page.evaluate(() => ({
    state: window.kiraHomeWorldDebug.activeAvatarState(),
    evidence: window.kiraHomeWorldDebug.embodimentEvidenceSnapshot("r6_exact_reach_after"),
  }));
  evidence.body_motion.turn_and_reach = {
    started: reachStarted,
    before: reachBefore,
    samples: reachSamples,
    after: reachAfter,
  };
  evidence.screenshots.turn_and_reach = await coveredScreenshot(
    page, reportDir, "turn_and_reach", "body",
    "PRIVATE EXACT-R6 BODY HIDDEN — numeric gradual-turn/door-reach evidence only",
  );

  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setActiveAvatarPosition({
      x: -1.1, y: 0.05, z: 11.8, roamZone: "kira_home_world", waitSeconds: 0,
    });
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 0);
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.focusKiraEyes({ distance: 0.21, y: 0.002 });
  });
  await page.waitForTimeout(700);
  const eyeCenter = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  evidence.screenshots.eye_center = await coveredScreenshot(
    page, reportDir, "eye_center", "head",
    "PRIVATE BODY COVER — exact-R6 staged-eye center view",
  );
  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeDirection("left"));
  await page.waitForTimeout(700);
  const eyeLeft = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeDirection("right"));
  await page.waitForTimeout(700);
  const eyeRight = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 1);
  });
  await page.waitForTimeout(220);
  const eyeBlinkBoth = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  evidence.screenshots.eye_blink = await coveredScreenshot(
    page, reportDir, "eye_blink", "head",
    "PRIVATE BODY COVER — exact-R6 staged-eye blink view",
  );
  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeBlink("left", 1));
  await page.waitForTimeout(120);
  const eyeBlinkLeft = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeBlink("right", 1));
  await page.waitForTimeout(120);
  const eyeBlinkRight = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 0);
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.startKiraArmMobilityTest(2.2);
  });
  const eyeBindingSamples = [];
  for (let index = 0; index < 6; index += 1) {
    eyeBindingSamples.push(await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding()));
    if (index < 5) await page.waitForTimeout(260);
  }
  const centerToLeft = vectorDelta(eyeCenter.leftEyeForward, eyeLeft.leftEyeForward);
  const centerToRight = vectorDelta(eyeCenter.leftEyeForward, eyeRight.leftEyeForward);
  const leftToRight = vectorDelta(eyeLeft.leftEyeForward, eyeRight.leftEyeForward);
  const maxBindingDelta = Math.max(...eyeBindingSamples.map((sample) => Number(sample.bindingDistanceDelta || 0)));
  const socketMotion = Math.max(...eyeBindingSamples.map((sample) => (
    vectorDelta(eyeBindingSamples[0].leftSocketWorld, sample.leftSocketWorld) || 0
  )));
  evidence.eyes = {
    center: eyeCenter,
    left: eyeLeft,
    right: eyeRight,
    blink_both: eyeBlinkBoth,
    blink_left: eyeBlinkLeft,
    blink_right: eyeBlinkRight,
    head_attachment_samples_during_voluntary_arm_mobility: eyeBindingSamples,
    metrics: {
      center_to_left_forward_delta: centerToLeft,
      center_to_right_forward_delta: centerToRight,
      left_to_right_forward_delta: leftToRight,
      max_binding_distance_delta_meters: maxBindingDelta,
      socket_motion_during_head_motion_meters: socketMotion,
    },
  };

  const mouthBefore = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  await page.evaluate(() => window.postMessage({
    type: "kira-voice-playback",
    playback: {
      revision: 6001,
      active: true,
      playing: true,
      phase: "chunk_playback",
      candidate: "kira",
      label: "Kira",
      chunk_index: 0,
      playback_started_at: Date.now() / 1000,
      isolated_r6_test: true,
    },
  }, "*"));
  await page.waitForFunction(() => {
    const probe = window.kiraHomeWorldDebug?.kiraExistingMouthLipSync?.();
    return Boolean(probe?.playingMatchedActiveAvatar && probe?.amount > 0.05);
  }, null, { timeout: 10_000 });
  const mouthPlaying = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  evidence.screenshots.mouth_playing = await coveredScreenshot(
    page, reportDir, "mouth_playing", "head",
    "PRIVATE BODY COVER — existing mouth deforms in place; no second mouth",
  );
  await page.evaluate(() => window.postMessage({
    type: "kira-voice-playback",
    playback: {
      revision: 6002,
      active: true,
      playing: false,
      phase: "chunk_playback_end",
      candidate: "kira",
      label: "Kira",
      chunk_index: 0,
      playback_ended_at: Date.now() / 1000,
      isolated_r6_test: true,
    },
  }, "*"));
  await page.waitForFunction(() => {
    const probe = window.kiraHomeWorldDebug?.kiraExistingMouthLipSync?.();
    return Boolean(probe?.active && probe?.restored && probe?.amount === 0 && !probe?.playingMatchedActiveAvatar);
  }, null, { timeout: 10_000 });
  const mouthAfter = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  evidence.mouth = { before: mouthBefore, while_playing: mouthPlaying, after: mouthAfter };

  const walkDisplacement = evidence.body_motion.walk.displacement_meters || 0;
  const walkBoundsFinite = walkSamples.every((sample) => finiteBounds(sample.bounds));
  const walkGrounded = walkSamples.every((sample) => sample.state?.visualGroundContact?.grounded !== false);
  const sitRootYOffset = Math.abs(Number(sitBefore.bounds?.rootPositionY) - Number(sitDuring.bounds?.rootPositionY));
  const sitBoundsMinYOffset = Math.abs(Number(sitBefore.bounds?.min?.y) - Number(sitDuring.bounds?.min?.y));
  const turnEvidenceSamples = reachSamples
    .map((sample) => sample.evidence?.mindBodyTruth?.body?.turnEvidence || sample.evidence?.transitionEvidence?.turnEvidence)
    .filter(Boolean);
  const rotations = [reachBefore.state.rotationY, ...reachSamples.map((sample) => sample.state.rotationY)]
    .filter(Number.isFinite);
  const rotationChanged = rotations.length > 1 && Math.max(...rotations) - Math.min(...rotations) > 0.05;
  const noInstantFlip = turnEvidenceSamples.length > 0 && turnEvidenceSamples.every((sample) => sample.instantFlip === false);
  const reachEvidenceSamples = reachSamples
    .map((sample) => sample.evidence?.mindBodyTruth?.body?.doorInteraction)
    .filter(Boolean);
  const bestHandDistance = Math.min(...reachEvidenceSamples
    .map((sample) => Number(sample.handContact?.distance))
    .filter(Number.isFinite), Infinity);
  const reachOpened = reachEvidenceSamples.some((sample) => sample.opened === true)
    || reachAfter.evidence?.mindBodyTruth?.body?.doorInteraction?.opened === true;
  const reachFailed = reachEvidenceSamples.some((sample) => sample.failed === true);
  const bothBlinkClosed = Object.values(eyeBlinkBoth.blinkMorphInfluences || {})
    .every((value) => Number(value) >= 0.99);
  const leftIndependent = Object.entries(eyeBlinkLeft.blinkMorphInfluences || {}).every(([name, value]) => (
    name.includes("Left") ? Number(value) >= 0.99 : Number(value) <= 0.01
  ));
  const rightIndependent = Object.entries(eyeBlinkRight.blinkMorphInfluences || {}).every(([name, value]) => (
    name.includes("Right") ? Number(value) >= 0.99 : Number(value) <= 0.01
  ));
  evidence.checks = {
    exact_r6_hash_loaded: before.r6_candidate.sha256 === EXPECTED_R6_SHA256
      && String(initial.state.modelUrl || "").includes("kira_provisional_body_r6.glb"),
    procedural_humanoid_rig_usable: initial.state.proceduralRig?.usable === true
      && initial.state.proceduralRig?.missing?.length === 0,
    initial_bounds_finite: finiteBounds(initial.bounds),
    walk_started_and_displaced: walkStarted === true && walkDisplacement > 0.3,
    walk_bounds_finite: walkBoundsFinite,
    walk_ground_contact_not_failed: walkGrounded,
    sit_started_and_deformed: sitStarted === true
      && sitDuring.state.action === "sit"
      && sitDuring.evidence?.postureState?.posture === "sit"
      && sitRootYOffset > 0.2
      && sitBoundsMinYOffset > 0.2
      && finiteBounds(sitDuring.bounds),
    gradual_turn_evidence: reachStarted === true && rotationChanged && noInstantFlip,
    front_door_reach_completed_without_failure: reachStarted === true
      && !reachFailed
      && (reachOpened || bestHandDistance <= 0.24),
    eye_structural_complete_and_head_bound: eyeCenter.active === true
      && eyeCenter.structural?.complete === true
      && eyeBindingSamples.every((sample) => sample.headBound === true),
    no_old_procedural_eye_nodes: eyeBindingSamples.every((sample) => sample.oldProceduralNodeCount === 0),
    eye_binding_invariant: maxBindingDelta <= 1e-7,
    eye_socket_followed_head_motion: socketMotion > 0.00001,
    lateral_gaze_changed: centerToLeft > 0.1 && centerToRight > 0.1 && leftToRight > 0.2,
    bilateral_blink: bothBlinkClosed,
    unilateral_blinks: leftIndependent && rightIndependent,
    existing_mouth_is_original_mesh: mouthBefore.active === true
      && mouthBefore.vertexCount === 207
      && mouthBefore.method === "in_place_existing_position_attribute_deformation",
    playback_boundary_deformed_and_restored_mouth: mouthPlaying.playingMatchedActiveAvatar === true
      && mouthPlaying.amount > 0.05
      && mouthAfter.restored === true
      && mouthAfter.amount === 0,
    no_second_mouth_created: mouthBefore.secondMouthCreated === false
      && mouthBefore.createdSceneNodes === 0
      && mouthBefore.meshCountBefore === mouthBefore.meshCountAfter
      && mouthPlaying.secondMouthCreated === false
      && mouthAfter.secondMouthCreated === false,
    no_runtime_errors: diagnostics.page_errors.length === 0
      && diagnostics.console_errors.length === 0
      && diagnostics.request_failures.length === 0
      && diagnostics.http_errors.length === 0,
  };
} catch (error) {
  fatalError = errorText(error);
  evidence.fatal_error = fatalError;
} finally {
  if (browser) await browser.close();
  if (assetServer) await new Promise((resolve) => assetServer.close(resolve));
  if (vite && !vite.killed) vite.kill();
  if (vite) {
    await new Promise((resolve) => {
      const timer = setTimeout(resolve, 3_000);
      vite.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });
    });
  }
}

const after = guardSnapshots();
evidence.guards.after = after;
for (const key of Object.keys(before)) evidence.guards.unchanged[key] = unchanged(before, after, key);
const guardChecks = {
  live_body_unchanged: evidence.guards.unchanged.live_body,
  runtime_selection_unchanged: evidence.guards.unchanged.runtime_selection,
  live_shell_unchanged_and_inactive: evidence.guards.unchanged.live_shell
    && !before.live_shell.active_candidate
    && !after.live_shell.active_candidate,
  preview_main_unchanged: evidence.guards.unchanged.preview_main,
  existing_mouth_controller_unchanged: evidence.guards.unchanged.existing_mouth_controller,
  server_main_unchanged_or_absent: evidence.guards.unchanged.server_main,
  exact_r6_asset_unchanged: evidence.guards.unchanged.r6_candidate,
  staged_eye_assets_unchanged: evidence.guards.unchanged.staged_eye && evidence.guards.unchanged.public_eye,
};
evidence.checks = { ...evidence.checks, ...guardChecks };
evidence.vite_output_tail = viteOutput;
evidence.status = !fatalError && Object.keys(evidence.checks).length > 0 && Object.values(evidence.checks).every(Boolean)
  ? "passed_inactive_technical_compatibility_only"
  : "failed_or_incomplete";
evidence.isolation.activation_allowed = false;
evidence.isolation.autobuild_allowed = false;

fs.writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
const failedChecks = Object.entries(evidence.checks).filter(([, passed]) => !passed).map(([name]) => name);
const markdown = [
  "# Exact Kira R6 inactive browser sandbox",
  "",
  `Generated: ${evidence.generated_at}`,
  `Status: **${evidence.status}**`,
  "",
  "## Exact artifact",
  "",
  `- Candidate: \`${relative(R6_PATH)}\``,
  `- SHA-256: \`${before.r6_candidate.sha256}\``,
  `- Expected SHA-256: \`${EXPECTED_R6_SHA256}\``,
  "",
  "## Isolation result",
  "",
  "No live person was activated, no life loop or audio playback was started, and no live model, selection, shell state, preview main, mouth controller, or server main file was intentionally changed. The renderer received the candidate only through a disposable browser page and loopback asset server.",
  "",
  "Runtime activation and avatar autobuild remain blocked regardless of the technical result.",
  "",
  "## Checks",
  "",
  ...Object.entries(evidence.checks).map(([name, passed]) => `- ${passed ? "PASS" : "FAIL"}: \`${name}\``),
  "",
  ...(fatalError ? ["## Fatal error", "", "```text", fatalError, "```", ""] : []),
  ...(failedChecks.length ? ["## Failed/incomplete gates", "", ...failedChecks.map((name) => `- \`${name}\``), ""] : []),
  "## Limits",
  "",
  ...evidence.limitations.map((item) => `- ${item}`),
  "",
  "All retained screenshots have an opaque privacy cover and `_covered` in the filename.",
  "",
  `Machine-readable evidence: \`${relative(evidencePath)}\``,
  "",
].join("\n");
fs.writeFileSync(markdownPath, markdown, "utf8");

process.stdout.write(`${JSON.stringify({
  status: evidence.status,
  report: relative(markdownPath),
  evidence: relative(evidencePath),
  candidate_sha256: before.r6_candidate.sha256,
  failed_checks: failedChecks,
  fatal_error: fatalError,
  guarded_files_unchanged: evidence.guards.unchanged,
}, null, 2)}\n`);
if (evidence.status === "failed_or_incomplete") process.exitCode = 1;
