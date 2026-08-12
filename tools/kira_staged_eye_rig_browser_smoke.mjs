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
const BODY_PATH = path.join(ROOT, "Avatar", "models", "temp_ai", "kira", "avatar.glb");
const STAGED_EYE_PATH = path.join(
  ROOT, "Avatar", "models", "staged", "kira", "eyes", "kira_brown_eye_rig_v3_2",
  "kira_brown_eye_rig_v3_2.glb",
);
const PUBLIC_EYE_PATH = path.join(
  PREVIEW_ROOT, "public", "models", "home_world", "kira", "kira_brown_eye_rig_v3_2.glb",
);
const SHELL_STATE_PATH = path.join(ROOT, "Data", "runtime", "kira_world_shell_state.json");
const REPORT_ROOT = path.join(ROOT, "Data", "world_tests", "kira_eye_upgrade_20260718", "browser");
const REPORT_PATH = path.join(REPORT_ROOT, "kira_staged_eye_rig_browser_smoke.json");

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function liveShellSnapshot() {
  if (!fs.existsSync(SHELL_STATE_PATH)) {
    return {
      exists: false,
      path: path.relative(ROOT, SHELL_STATE_PATH).replaceAll("\\", "/"),
      active_candidate: null,
      active_conversation_mode: null,
      sha256: null,
    };
  }
  const raw = fs.readFileSync(SHELL_STATE_PATH);
  const state = JSON.parse(raw.toString("utf8"));
  return {
    exists: true,
    path: path.relative(ROOT, SHELL_STATE_PATH).replaceAll("\\", "/"),
    active_candidate: String(state.active_candidate || ""),
    active_conversation_mode: String(state.active_conversation_mode || ""),
    updated_at: state.updated_at || null,
    sha256: crypto.createHash("sha256").update(raw).digest("hex"),
  };
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
      "Content-Type": path.extname(resolved).toLowerCase() === ".glb" ? "model/gltf-binary" : "application/octet-stream",
      "Content-Length": fs.statSync(resolved).size,
    });
    fs.createReadStream(resolved).pipe(response);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

function vectorDelta(a, b) {
  if (!a || !b) return null;
  return Number(Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z).toFixed(9));
}

for (const required of [BODY_PATH, STAGED_EYE_PATH, PUBLIC_EYE_PATH]) {
  if (!fs.existsSync(required)) throw new Error(`Missing required asset: ${required}`);
}
fs.mkdirSync(REPORT_ROOT, { recursive: true });

const stagedHash = sha256(STAGED_EYE_PATH);
const publicHash = sha256(PUBLIC_EYE_PATH);
const bodyHashBefore = sha256(BODY_PATH);
const liveShellBefore = liveShellSnapshot();
if (stagedHash !== publicHash) throw new Error(`Public eye asset hash mismatch: ${stagedHash} != ${publicHash}`);
if (liveShellBefore.exists && liveShellBefore.active_candidate) {
  throw new Error(`Refusing isolated eye smoke while live candidate is active: ${liveShellBefore.active_candidate}`);
}

const vitePort = await freePort();
const assetPort = await freePort();
const worldUrl = `http://127.0.0.1:${vitePort}/?area=home&motionSmoke=1`;
const bodyUrl = `http://127.0.0.1:${assetPort}/Avatar/models/temp_ai/kira/avatar.glb?v=${fs.statSync(BODY_PATH).mtimeMs}`;
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
  await page.evaluate((url) => window.kiraHomeWorldDebug.injectShellState({
    active_candidate: "kira",
    active_label: "Kira",
    active_ai: "Kira",
    active_form: "civilian",
    active_action: "idle",
    active_model_url: url,
    active_pose_manifest_url: "",
    location: "home",
    isolated_browser_test: true,
  }), bodyUrl);
  await page.waitForFunction(() => {
    const state = window.kiraHomeWorldDebug?.kiraEyeStatus?.();
    return Boolean(state?.active && state?.structural?.complete && state?.headBound);
  }, null, { timeout: 120_000 });
  await page.waitForTimeout(1_000);

  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 0);
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.focusKiraEyes({ distance: 0.21, y: 0.002 });
  });
  await page.waitForTimeout(700);
  const centerStatus = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  const defaultOnNodeNames = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarModelNodeNames());
  const centerScreenshot = path.join(REPORT_ROOT, "center.png");
  await page.screenshot({ path: centerScreenshot });

  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeDirection("left"));
  await page.waitForTimeout(700);
  const leftStatus = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  const leftScreenshot = path.join(REPORT_ROOT, "look_left.png");
  await page.screenshot({ path: leftScreenshot });

  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeDirection("right"));
  await page.waitForTimeout(700);
  const rightStatus = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  const rightScreenshot = path.join(REPORT_ROOT, "look_right.png");
  await page.screenshot({ path: rightScreenshot });

  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 1);
  });
  await page.waitForTimeout(220);
  const blinkStatus = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  const blinkScreenshot = path.join(REPORT_ROOT, "blink_both.png");
  await page.screenshot({ path: blinkScreenshot });

  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeBlink("left", 1));
  await page.waitForTimeout(120);
  const blinkLeftStatus = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeBlink("right", 1));
  await page.waitForTimeout(120);
  const blinkRightStatus = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());

  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 0);
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.startKiraDoctorBodyControlExam({ phaseSeconds: 0.8 });
  });
  const bindingSamples = [];
  for (let index = 0; index < 5; index += 1) {
    bindingSamples.push(await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding()));
    if (index < 4) await page.waitForTimeout(260);
  }

  const optOutPage = await context.newPage();
  optOutPage.on("pageerror", (error) => diagnostics.page_errors.push(error.message));
  optOutPage.on("console", (message) => {
    if (message.type() === "error") diagnostics.console_errors.push(message.text());
  });
  optOutPage.on("requestfailed", (request) => diagnostics.request_failures.push({
    url: request.url(),
    error: request.failure()?.errorText || "failed",
  }));
  optOutPage.on("response", (response) => {
    if (response.status() >= 400) diagnostics.http_errors.push({ status: response.status(), url: response.url() });
  });
  await optOutPage.goto(`http://127.0.0.1:${vitePort}/?area=home&motionSmoke=1&kiraEyeRig=off`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  await optOutPage.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.injectShellState), null, { timeout: 120_000 });
  await optOutPage.evaluate((url) => window.kiraHomeWorldDebug.injectShellState({
    active_candidate: "kira",
    active_label: "Kira",
    active_ai: "Kira",
    active_form: "civilian",
    active_action: "idle",
    active_model_url: url,
    active_pose_manifest_url: "",
    location: "home",
    isolated_browser_eye_opt_out_test: true,
  }), bodyUrl);
  await optOutPage.waitForFunction(() => {
    const debug = window.kiraHomeWorldDebug;
    const nodes = debug?.activeAvatarModelNodeNames?.() || [];
    return Boolean(debug?.activeAvatarState?.().rootPresent)
      && nodes.some((name) => /mixamorig|head_06/i.test(String(name)));
  }, null, { timeout: 120_000 });
  await optOutPage.waitForTimeout(600);
  const optOutStatus = await optOutPage.evaluate(() => window.kiraHomeWorldDebug.kiraEyeStatus());
  const optOutNodeNames = await optOutPage.evaluate(() => window.kiraHomeWorldDebug.activeAvatarModelNodeNames());
  await optOutPage.close();

  const explicitPage = await context.newPage();
  explicitPage.on("pageerror", (error) => diagnostics.page_errors.push(error.message));
  explicitPage.on("console", (message) => {
    if (message.type() === "error") diagnostics.console_errors.push(message.text());
  });
  explicitPage.on("requestfailed", (request) => diagnostics.request_failures.push({
    url: request.url(),
    error: request.failure()?.errorText || "failed",
  }));
  explicitPage.on("response", (response) => {
    if (response.status() >= 400) diagnostics.http_errors.push({ status: response.status(), url: response.url() });
  });
  await explicitPage.goto(`http://127.0.0.1:${vitePort}/?area=home&motionSmoke=1&kiraEyeRig=v3.2`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  await explicitPage.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.injectShellState), null, { timeout: 120_000 });
  await explicitPage.evaluate((url) => window.kiraHomeWorldDebug.injectShellState({
    active_candidate: "kira",
    active_label: "Kira",
    active_ai: "Kira",
    active_form: "civilian",
    active_action: "idle",
    active_model_url: url,
    active_pose_manifest_url: "",
    location: "home",
    isolated_browser_explicit_v3_2_test: true,
  }), bodyUrl);
  await explicitPage.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.kiraEyeStatus?.().active), null, { timeout: 120_000 });
  const explicitVersionStatus = await explicitPage.evaluate(() => window.kiraHomeWorldDebug.kiraEyeStatus());
  await explicitPage.close();

  const centerToLeft = vectorDelta(centerStatus.leftEyeForward, leftStatus.leftEyeForward);
  const centerToRight = vectorDelta(centerStatus.leftEyeForward, rightStatus.leftEyeForward);
  const leftToRight = vectorDelta(leftStatus.leftEyeForward, rightStatus.leftEyeForward);
  const allBlinkClosed = Object.values(blinkStatus.blinkMorphInfluences || {}).every((value) => Number(value) >= 0.99);
  const unilateralLeft = Object.entries(blinkLeftStatus.blinkMorphInfluences || {}).every(([name, value]) => (
    name.includes("Left") ? Number(value) >= 0.99 : Number(value) <= 0.01
  ));
  const unilateralRight = Object.entries(blinkRightStatus.blinkMorphInfluences || {}).every(([name, value]) => (
    name.includes("Right") ? Number(value) >= 0.99 : Number(value) <= 0.01
  ));
  const maxBindingDelta = Math.max(...bindingSamples.map((sample) => Number(sample.bindingDistanceDelta || 0)));
  const socketMotionDuringHeadTest = Math.max(...bindingSamples.map((sample) => vectorDelta(bindingSamples[0].leftSocketWorld, sample.leftSocketWorld) || 0));
  const bodyHashAfter = sha256(BODY_PATH);
  const liveShellAfter = liveShellSnapshot();
  const statusChecks = {
    exact_hash_copy: stagedHash === publicHash,
    active_body_hash_unchanged: bodyHashBefore === bodyHashAfter,
    live_kira_inactive_before_and_after: (!liveShellBefore.exists || !liveShellBefore.active_candidate)
      && (!liveShellAfter.exists || !liveShellAfter.active_candidate),
    live_shell_state_unchanged: liveShellBefore.sha256 === liveShellAfter.sha256,
    default_url_attached_eye_rig: centerStatus.active === true
      && centerStatus.defaultEnabled === true
      && defaultOnNodeNames.includes("KiraBrownEyeRig_v3_2"),
    opt_out_url_did_not_attach_eye_rig: optOutStatus.active === false
      && optOutStatus.enabled === false
      && !optOutNodeNames.includes("KiraBrownEyeRig_v3_2"),
    explicit_v3_2_url_attached_eye_rig: explicitVersionStatus.active === true,
    structural_complete: centerStatus.structural?.complete === true,
    head_bound: bindingSamples.every((sample) => sample.headBound === true),
    no_old_procedural_nodes: bindingSamples.every((sample) => sample.oldProceduralNodeCount === 0),
    binding_distance_invariant: maxBindingDelta <= 1e-7,
    eye_socket_followed_head_motion: socketMotionDuringHeadTest > 0.00001,
    lateral_gaze_changed: centerToLeft > 0.1 && centerToRight > 0.1 && leftToRight > 0.2,
    both_blink_closed: allBlinkClosed,
    left_blink_independent: unilateralLeft,
    right_blink_independent: unilateralRight,
    no_runtime_errors: diagnostics.page_errors.length === 0
      && diagnostics.console_errors.length === 0
      && diagnostics.request_failures.length === 0
      && diagnostics.http_errors.length === 0,
  };
  const report = {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    status: Object.values(statusChecks).every(Boolean) ? "passed_default_on_reversible_eye_runtime_checks" : "failed_or_incomplete",
    isolation: {
      live_person_activated: false,
      life_loop_started: false,
      shell_state_persisted: false,
      runtime_mode: "default-on with no kiraEyeRig parameter",
      opt_out_flag: "?kiraEyeRig=off",
      explicit_version_flag: "?kiraEyeRig=v3.2",
      default_enabled: true,
      live_shell_before: liveShellBefore,
      live_shell_after: liveShellAfter,
    },
    assets: {
      body_path: path.relative(ROOT, BODY_PATH).replaceAll("\\", "/"),
      body_sha256_before: bodyHashBefore,
      body_sha256_after: bodyHashAfter,
      body_unchanged: bodyHashBefore === bodyHashAfter,
      staged_eye_path: path.relative(ROOT, STAGED_EYE_PATH).replaceAll("\\", "/"),
      staged_eye_sha256: stagedHash,
      public_eye_path: path.relative(ROOT, PUBLIC_EYE_PATH).replaceAll("\\", "/"),
      public_eye_sha256: publicHash,
    },
    checks: statusChecks,
    metrics: {
      center_to_left_forward_delta: centerToLeft,
      center_to_right_forward_delta: centerToRight,
      left_to_right_forward_delta: leftToRight,
      max_binding_distance_delta_meters: maxBindingDelta,
      eye_socket_motion_during_head_exam_meters: socketMotionDuringHeadTest,
    },
    center: centerStatus,
    look_left: leftStatus,
    look_right: rightStatus,
    blink_both: blinkStatus,
    blink_left: blinkLeftStatus,
    blink_right: blinkRightStatus,
    default_on_runtime: {
      status: centerStatus,
      staged_root_present_in_avatar_nodes: defaultOnNodeNames.includes("KiraBrownEyeRig_v3_2"),
    },
    opt_out_runtime: {
      status: optOutStatus,
      staged_root_present_in_avatar_nodes: optOutNodeNames.includes("KiraBrownEyeRig_v3_2"),
    },
    explicit_v3_2_runtime: {
      status: explicitVersionStatus,
    },
    binding_samples_during_head_exam: bindingSamples,
    visual_review: {
      performed_by_script: false,
      claim: "Screenshots are evidence for human review; numeric checks alone do not establish facial realism.",
    },
    screenshots: {
      center: path.relative(ROOT, centerScreenshot).replaceAll("\\", "/"),
      look_left: path.relative(ROOT, leftScreenshot).replaceAll("\\", "/"),
      look_right: path.relative(ROOT, rightScreenshot).replaceAll("\\", "/"),
      blink_both: path.relative(ROOT, blinkScreenshot).replaceAll("\\", "/"),
    },
    diagnostics,
    vite_output_tail: viteOutput,
  };
  fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({
    status: report.status,
    checks: report.checks,
    metrics: report.metrics,
    screenshots: report.screenshots,
    diagnostics,
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
