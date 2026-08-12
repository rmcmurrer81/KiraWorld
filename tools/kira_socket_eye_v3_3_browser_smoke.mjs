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
const BODY_RELATIVE_PATH = path.join(
  "Avatar", "avatar_builder", "candidate_sources", "kira_provisional_body_r6",
  "r6_20260718_163658", "kira_provisional_body_r6.glb",
);
const BODY_PATH = path.join(ROOT, BODY_RELATIVE_PATH);
const STAGED_EYE_PATH = path.join(
  ROOT, "Avatar", "models", "staged", "kira", "eyes", "kira_socket_eye_rig_v3_3",
  "kira_socket_eye_rig_v3_3.glb",
);
const PUBLIC_EYE_PATH = path.join(
  PREVIEW_ROOT, "public", "models", "home_world", "kira", "kira_socket_eye_rig_v3_3.glb",
);
const EXPECTED_R6_BODY_SHA256 = "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77";
const EXPECTED_EYE_SHA256 = "b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5";
const SHELL_STATE_PATH = path.join(ROOT, "Data", "runtime", "kira_world_shell_state.json");
const REPORT_SUFFIX = String(process.env.KIRA_EYE_REPORT_SUFFIX || "browser")
  .replace(/[^a-zA-Z0-9_.-]+/g, "_");
const REPORT_ROOT = path.join(ROOT, "Data", "world_tests", "kira_socket_eye_v3_3_20260722", REPORT_SUFFIX);
const REPORT_PATH = path.join(REPORT_ROOT, "evidence.json");
const EYE_BINDING_MODE = ["root", "skin"].includes(process.env.KIRA_EYE_BINDING_MODE)
  ? process.env.KIRA_EYE_BINDING_MODE
  : "skin";
const IRIS_DEPTH_TEST_MODE = process.env.KIRA_EYE_IRIS_DEPTH_TEST === "off" ? "off" : "on";
const REQUESTED_VISUAL_FIT = Object.fromEntries([
  ["forwardOffset", process.env.KIRA_EYE_FIT_FORWARD],
  ["verticalOffset", process.env.KIRA_EYE_FIT_VERTICAL],
  ["horizontalOffset", process.env.KIRA_EYE_FIT_HORIZONTAL],
  ["commonHorizontalOffset", process.env.KIRA_EYE_FIT_COMMON_HORIZONTAL],
  ["neutralYawDegrees", process.env.KIRA_EYE_FIT_YAW],
  ["irisHorizontalOffset", process.env.KIRA_EYE_FIT_IRIS_HORIZONTAL],
  ["irisVerticalOffset", process.env.KIRA_EYE_FIT_IRIS_VERTICAL],
  ["irisDepthOffset", process.env.KIRA_EYE_FIT_IRIS_DEPTH],
  ["socketVerticalOffset", process.env.KIRA_EYE_FIT_SOCKET_VERTICAL],
  ["socketDepthOffset", process.env.KIRA_EYE_FIT_SOCKET_DEPTH],
].filter(([, value]) => value !== undefined && value !== "").map(([key, value]) => [key, Number(value)]));

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function shellSnapshot() {
  if (!fs.existsSync(SHELL_STATE_PATH)) return { exists: false, activeCandidate: "", sha256: null };
  const raw = fs.readFileSync(SHELL_STATE_PATH);
  const state = JSON.parse(raw.toString("utf8"));
  return {
    exists: true,
    activeCandidate: String(state.active_candidate || ""),
    conversationMode: String(state.active_conversation_mode || ""),
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
  return Number(Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z).toFixed(10));
}

for (const required of [BODY_PATH, STAGED_EYE_PATH, PUBLIC_EYE_PATH]) {
  if (!fs.existsSync(required)) throw new Error(`Missing required asset: ${required}`);
}
fs.mkdirSync(REPORT_ROOT, { recursive: true });

const stagedHash = sha256(STAGED_EYE_PATH);
const publicHash = sha256(PUBLIC_EYE_PATH);
const bodyHashBefore = sha256(BODY_PATH);
const shellBefore = shellSnapshot();
if (shellBefore.exists && shellBefore.activeCandidate) {
  throw new Error(`Refusing isolated eye smoke while a live person is active: ${shellBefore.activeCandidate}`);
}

const vitePort = await freePort();
const assetPort = await freePort();
const baseWorldUrl = `http://127.0.0.1:${vitePort}/?area=home&motionSmoke=1&kiraEyeBinding=${EYE_BINDING_MODE}&kiraEyeIrisDepthTest=${IRIS_DEPTH_TEST_MODE}`;
const bodyUrl = `http://127.0.0.1:${assetPort}/${BODY_RELATIVE_PATH.replaceAll("\\", "/")}?v=${fs.statSync(BODY_PATH).mtimeMs}`;
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
const diagnostics = { pageErrors: [], consoleErrors: [], requestFailures: [], httpErrors: [] };

async function instrumentPage(page) {
  page.on("pageerror", (error) => diagnostics.pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => diagnostics.requestFailures.push({
    url: request.url(),
    error: request.failure()?.errorText || "failed",
  }));
  page.on("response", (response) => {
    if (response.status() >= 400) diagnostics.httpErrors.push({ status: response.status(), url: response.url() });
  });
}

async function injectIsolatedKira(page, url) {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.injectShellState), null, { timeout: 120_000 });
  await page.evaluate((modelUrl) => window.kiraHomeWorldDebug.injectShellState({
    active_candidate: "kira",
    active_label: "Kira",
    active_ai: "Kira",
    active_form: "civilian",
    active_action: "idle",
    active_model_url: modelUrl,
    active_pose_manifest_url: "",
    location: "home",
    isolated_browser_test: true,
  }), bodyUrl);
}

async function waitForEyeRig(page) {
  await page.waitForFunction((bindingMode) => {
    const state = window.kiraHomeWorldDebug?.kiraEyeStatus?.();
    return Boolean(state?.active && state?.structural?.complete && (
      state?.headBound || bindingMode === "root"
    ));
  }, EYE_BINDING_MODE, { timeout: 120_000 });
  await page.waitForTimeout(900);
}

async function setDirectionAndCapture(page, direction, filename) {
  await page.evaluate((value) => window.kiraHomeWorldDebug.setKiraEyeDirection(value), direction);
  await page.waitForTimeout(900);
  const status = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  const screenshotPath = path.join(REPORT_ROOT, filename);
  await page.screenshot({ path: screenshotPath });
  return { status, screenshotPath };
}

try {
  assetServer = await startAssetServer(assetPort);
  await waitForHttp(baseWorldUrl);
  browser = await chromium.launch({
    headless: true,
    args: ["--use-angle=default", "--enable-webgl", "--ignore-gpu-blocklist"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await instrumentPage(page);
  await injectIsolatedKira(page, baseWorldUrl);
  await waitForEyeRig(page);
  if (Object.keys(REQUESTED_VISUAL_FIT).length > 0) {
    await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit), REQUESTED_VISUAL_FIT);
    await page.waitForTimeout(350);
  }
  await page.evaluate(() => window.kiraHomeWorldDebug.focusKiraEyes({ distance: 0.28, y: 0.002 }));
  await page.waitForTimeout(500);

  const center = await setDirectionAndCapture(page, "center", "center.png");
  const left = await setDirectionAndCapture(page, "left", "look_left.png");
  const right = await setDirectionAndCapture(page, "right", "look_right.png");
  const up = await setDirectionAndCapture(page, "up", "look_up.png");
  const down = await setDirectionAndCapture(page, "down", "look_down.png");
  const blinkResult = await page.evaluate(() => window.kiraHomeWorldDebug.setKiraEyeBlink("both", 1));
  await page.waitForTimeout(200);
  const afterBlinkRequest = await page.evaluate(() => window.kiraHomeWorldDebug.probeKiraEyeBinding());
  const nodeNames = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarModelNodeNames());

  const optOutPage = await context.newPage();
  await instrumentPage(optOutPage);
  await injectIsolatedKira(optOutPage, `${baseWorldUrl}&kiraEyeRig=off`);
  await optOutPage.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.activeAvatarState?.().rootPresent), null, { timeout: 120_000 });
  await optOutPage.waitForTimeout(700);
  const optOutStatus = await optOutPage.evaluate(() => window.kiraHomeWorldDebug.kiraEyeStatus());
  const optOutNodeNames = await optOutPage.evaluate(() => window.kiraHomeWorldDebug.activeAvatarModelNodeNames());
  await optOutPage.close();

  const explicitPage = await context.newPage();
  await instrumentPage(explicitPage);
  await injectIsolatedKira(explicitPage, `${baseWorldUrl}&kiraEyeRig=v3.3`);
  await waitForEyeRig(explicitPage);
  const explicitStatus = await explicitPage.evaluate(() => window.kiraHomeWorldDebug.kiraEyeStatus());
  await explicitPage.close();

  const fixedNodeKeys = [
    "leftSocketLocal", "rightSocketLocal",
    "leftScleraLocal", "rightScleraLocal",
    "leftCorneaLocal", "rightCorneaLocal",
  ];
  const directionalStates = [left.status, right.status, up.status, down.status];
  const maxFixedSurfaceMotion = Math.max(...directionalStates.flatMap((state) => (
    fixedNodeKeys.map((key) => vectorDelta(center.status[key], state[key]) || 0)
  )));
  const horizontalIrisTravel = vectorDelta(left.status.leftIrisLocal, right.status.leftIrisLocal) || 0;
  const verticalIrisTravel = vectorDelta(up.status.leftIrisLocal, down.status.leftIrisLocal) || 0;
  const maxHeadBindingDistanceDelta = Math.max(...[center, left, right, up, down]
    .map(({ status }) => Math.abs(Number(status.bindingDistanceDelta || 0))));

  const bodyHashAfter = sha256(BODY_PATH);
  const shellAfter = shellSnapshot();
  const checks = {
    exact_current_r6_body_hash: bodyHashBefore === EXPECTED_R6_BODY_SHA256,
    exact_reviewed_eye_hash: stagedHash === EXPECTED_EYE_SHA256 && publicHash === EXPECTED_EYE_SHA256,
    active_body_hash_unchanged: bodyHashBefore === bodyHashAfter,
    no_live_person_activated: (!shellBefore.exists || !shellBefore.activeCandidate)
      && (!shellAfter.exists || !shellAfter.activeCandidate),
    live_shell_state_unchanged: shellBefore.sha256 === shellAfter.sha256,
    default_url_attached_v3_3: center.status.active === true
      && center.status.version === "3.3.0"
      && nodeNames.includes("KiraBrownEyeRig_R7_V3_SocketSeated"),
    explicit_v3_3_url_attached: explicitStatus.active === true && explicitStatus.version === "3.3.0",
    opt_out_url_did_not_attach: optOutStatus.active === false
      && optOutStatus.enabled === false
      && !optOutNodeNames.includes("KiraBrownEyeRig_R7_V3_SocketSeated"),
    structural_complete: center.status.structural?.complete === true,
    head_bound: EYE_BINDING_MODE === "root" || center.status.headBound === true,
    head_binding_distance_stable: EYE_BINDING_MODE === "root"
      || maxHeadBindingDistanceDelta <= 0.000001,
    no_old_procedural_eye_nodes: center.status.oldProceduralNodeCount === 0,
    gaze_moves_only_iris_surface: horizontalIrisTravel >= 0.0015
      && verticalIrisTravel >= 0.0008
      && maxFixedSurfaceMotion <= 0.000001,
    blink_fails_honestly_without_fake_lids: blinkResult === false
      && afterBlinkRequest.blinkSupported === false
      && afterBlinkRequest.blinkUnsupportedRequest?.reason === "no_visually_approved_skinned_eyelid_geometry",
    no_runtime_errors: diagnostics.pageErrors.length === 0
      && diagnostics.consoleErrors.length === 0
      && diagnostics.requestFailures.length === 0
      && diagnostics.httpErrors.length === 0,
  };
  const screenshots = {
    center: path.relative(ROOT, center.screenshotPath).replaceAll("\\", "/"),
    lookLeft: path.relative(ROOT, left.screenshotPath).replaceAll("\\", "/"),
    lookRight: path.relative(ROOT, right.screenshotPath).replaceAll("\\", "/"),
    lookUp: path.relative(ROOT, up.screenshotPath).replaceAll("\\", "/"),
    lookDown: path.relative(ROOT, down.screenshotPath).replaceAll("\\", "/"),
  };
  const report = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    status: Object.values(checks).every(Boolean) ? "passed" : "failed_or_incomplete",
    isolation: {
      livePersonActivated: false,
      lifeLoopStarted: false,
      shellStatePersisted: false,
      defaultEnabled: true,
      optOutFlag: "?kiraEyeRig=off",
      explicitVersionFlag: "?kiraEyeRig=v3.3",
      shellBefore,
      shellAfter,
    },
    assets: {
      bodyPath: path.relative(ROOT, BODY_PATH).replaceAll("\\", "/"),
      bodySha256Before: bodyHashBefore,
      bodySha256After: bodyHashAfter,
      stagedEyePath: path.relative(ROOT, STAGED_EYE_PATH).replaceAll("\\", "/"),
      stagedEyeSha256: stagedHash,
      publicEyePath: path.relative(ROOT, PUBLIC_EYE_PATH).replaceAll("\\", "/"),
      publicEyeSha256: publicHash,
    },
    requestedVisualFit: REQUESTED_VISUAL_FIT,
    requestedBindingMode: EYE_BINDING_MODE,
    checks,
    metrics: {
      horizontalIrisTravelMeters: horizontalIrisTravel,
      verticalIrisTravelMeters: verticalIrisTravel,
      maxSocketScleraCorneaLocalMotionMeters: maxFixedSurfaceMotion,
      maxHeadBindingDistanceDeltaMeters: maxHeadBindingDistanceDelta,
    },
    center: center.status,
    left: left.status,
    right: right.status,
    up: up.status,
    down: down.status,
    afterUnsupportedBlinkRequest: afterBlinkRequest,
    optOutStatus,
    explicitStatus,
    screenshots,
    visualReview: {
      performedByScript: false,
      claim: "Screenshots require original-resolution visual review; numeric checks do not prove facial realism.",
    },
    diagnostics,
    viteOutputTail: viteOutput,
  };
  fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: report.status, checks, metrics: report.metrics, screenshots, diagnostics }, null, 2)}\n`);
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
