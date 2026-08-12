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
const BODY_PATH = path.join(
  ROOT,
  "Avatar", "avatar_builder", "candidate_sources", "kira_provisional_body_r6",
  "r6_20260718_163658", "kira_provisional_body_r6.glb",
);
const BODY_SHA256 = "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77";
const EYE_PATH = path.join(
  ROOT,
  "Avatar", "models", "staged", "kira", "eyes", "kira_brown_eye_rig_v3_2",
  "kira_brown_eye_rig_v3_2.glb",
);
const EYE_SHA256 = "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413";
const DEFAULT_REPORT_ROOT = path.join(ROOT, "Data", "world_tests", "kira_r6_eye_fit_candidate_20260721");
const REPORT_ROOT = process.env.KIRA_EYE_REPORT_ROOT
  ? path.resolve(ROOT, process.env.KIRA_EYE_REPORT_ROOT)
  : DEFAULT_REPORT_ROOT;
const REPORT_PATH = path.join(REPORT_ROOT, "depth_sweep_evidence.json");

// These offsets are derived from exact-R6 aperture centroids.  The sweep varies
// only depth because ray-cast geometry cannot prove front/back occlusion.
const CENTERED_GEOMETRY_FIT = Object.freeze({
  verticalOffset: 0.000004266304348021777,
  horizontalOffset: -0.00002159646739130147,
  commonHorizontalOffset: 0,
  neutralYawDegrees: 0,
  irisHorizontalOffset: 0,
  irisVerticalOffset: 0,
});
const REVIEW_BASE_FIT = Object.freeze({
  ...CENTERED_GEOMETRY_FIT,
  ...(process.env.KIRA_EYE_BASE_FIT_JSON
    ? JSON.parse(process.env.KIRA_EYE_BASE_FIT_JSON)
    : {}),
});
const DEPTHS = process.env.KIRA_EYE_DEPTHS
  ? process.env.KIRA_EYE_DEPTHS.split(",").map((value) => Number(value.trim()))
  : [-0.012, -0.008, -0.004, 0, 0.004, 0.008];
if (!DEPTHS.length || DEPTHS.some((value) => !Number.isFinite(value) || value < -0.02 || value > 0.03)) {
  throw new Error("KIRA_EYE_DEPTHS must contain comma-separated finite offsets inside the reversible runtime clamp.");
}
const CAMERA_YAWS = process.env.KIRA_EYE_CAMERA_YAWS
  ? process.env.KIRA_EYE_CAMERA_YAWS.split(",").map((value) => Number(value.trim()))
  : [0];
if (!CAMERA_YAWS.length || CAMERA_YAWS.some((value) => !Number.isFinite(value) || value < -90 || value > 90)) {
  throw new Error("KIRA_EYE_CAMERA_YAWS must contain comma-separated finite angles between -90 and +90 degrees.");
}

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function record(filePath) {
  return {
    path: path.relative(ROOT, filePath).replaceAll("\\", "/"),
    bytes: fs.statSync(filePath).size,
    sha256: sha256(filePath),
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

function rotateAroundWorldY(direction, degrees) {
  const radians = degrees * Math.PI / 180;
  const cosine = Math.cos(radians);
  const sine = Math.sin(radians);
  return {
    x: direction.x * cosine + direction.z * sine,
    y: direction.y,
    z: -direction.x * sine + direction.z * cosine,
  };
}

if (sha256(BODY_PATH) !== BODY_SHA256) throw new Error("Exact R6 body hash changed; refusing depth sweep.");
if (sha256(EYE_PATH) !== EYE_SHA256) throw new Error("Exact staged-eye hash changed; refusing depth sweep.");
fs.mkdirSync(REPORT_ROOT, { recursive: true });

const bodyHashBefore = sha256(BODY_PATH);
const eyeHashBefore = sha256(EYE_PATH);
const vitePort = await freePort();
const assetPort = await freePort();
const bodyRelative = path.relative(ROOT, BODY_PATH).replaceAll("\\", "/");
const worldUrl = `http://127.0.0.1:${vitePort}/?area=home&motionSmoke=1&kiraEyeIdleFit=off`;
const bodyUrl = `http://127.0.0.1:${assetPort}/${bodyRelative}?v=${fs.statSync(BODY_PATH).mtimeMs}`;
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
const diagnostics = { page_errors: [], console_errors: [], request_failures: [] };
let evidence = { status: "failed", note: "Depth sweep did not finish." };

try {
  assetServer = await startAssetServer(assetPort);
  await waitForHttp(worldUrl);
  browser = await chromium.launch({
    headless: true,
    args: ["--use-angle=default", "--enable-webgl", "--ignore-gpu-blocklist"],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (error) => diagnostics.page_errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.console_errors.push(message.text());
  });
  page.on("requestfailed", (request) => diagnostics.request_failures.push({
    url: request.url(),
    error: request.failure()?.errorText || "failed",
  }));

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
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.activeAvatarState?.().rootPresent), null, { timeout: 120_000 });
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.kiraEyeRig?.()?.active), null, { timeout: 30_000 });
  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 0);
  });

  const originalProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const originalFit = originalProbe.runtimeVisualFit?.eyeGlobeTranslation || {};

  // Establish a fit-independent head-forward direction and fixed socket target.
  const axisFit = { ...REVIEW_BASE_FIT, forwardOffset: 0 };
  await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit), axisFit);
  await page.waitForTimeout(1_200);
  const axisProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const headForward = axisProbe.leftEyeForward;
  const left = axisProbe.leftSocketWorld;
  const right = axisProbe.rightSocketWorld;
  if (!headForward || !left || !right) throw new Error("Could not establish head-relative eye framing.");
  const target = {
    x: (left.x + right.x) * 0.5,
    y: (left.y + right.y) * 0.5,
    z: (left.z + right.z) * 0.5,
  };

  const screenshots = {};
  for (const forwardOffset of DEPTHS) {
    const fit = { ...REVIEW_BASE_FIT, forwardOffset };
    await page.evaluate((candidate) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(candidate), fit);
    await page.waitForTimeout(1_000);
    const depthId = forwardOffset < 0
      ? `depth_neg_${String(Math.abs(forwardOffset * 1000)).padStart(2, "0")}mm`
      : `depth_pos_${String(Math.abs(forwardOffset * 1000)).padStart(2, "0")}mm`;
    for (const cameraYawDegrees of CAMERA_YAWS) {
      // Re-read the head/socket frame immediately before every image.  Kira's
      // ambient head micro-movement remains active in this isolated browser,
      // so a camera frozen to the first frame would turn a depth trial into a
      // misleading off-axis/temple view.  Each image is fixed relative to the
      // current head frame instead.
      const frameProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
      const frameForward = frameProbe.leftPivotParentBasis?.localZInWorld || frameProbe.leftEyeForward;
      const frameLeft = frameProbe.leftSocketWorld;
      const frameRight = frameProbe.rightSocketWorld;
      if (!frameForward || !frameLeft || !frameRight) throw new Error("Could not read current head-relative review frame.");
      const frameTarget = {
        x: (frameLeft.x + frameRight.x) * 0.5,
        y: (frameLeft.y + frameRight.y) * 0.5,
        z: (frameLeft.z + frameRight.z) * 0.5,
      };
      const direction = rotateAroundWorldY(frameForward, cameraYawDegrees);
      const distance = 0.34;
      const eye = {
        x: frameTarget.x + direction.x * distance,
        y: frameTarget.y + 0.003,
        z: frameTarget.z + direction.z * distance,
      };
      const dx = frameTarget.x - eye.x;
      const dz = frameTarget.z - eye.z;
      const dy = frameTarget.y - eye.y;
      const yaw = Math.atan2(-dx, -dz);
      const pitch = Math.atan2(dy, Math.max(0.001, Math.hypot(dx, dz)));
      await page.evaluate((camera) => window.kiraHomeWorldDebug.setPlayerPosition({ ...camera, floor: 0 }), {
        ...eye,
        yaw,
        pitch,
      });
      await page.waitForTimeout(40);
      const viewId = cameraYawDegrees === 0
        ? "front"
        : cameraYawDegrees < 0
          ? `left_${String(Math.abs(cameraYawDegrees)).padStart(2, "0")}deg`
          : `right_${String(Math.abs(cameraYawDegrees)).padStart(2, "0")}deg`;
      const id = `${depthId}_${viewId}`;
      const outputPath = path.join(REPORT_ROOT, `${id}.png`);
      await page.screenshot({ path: outputPath });
      const probe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
      screenshots[id] = {
        ...record(outputPath),
        fit,
        camera_yaw_degrees: cameraYawDegrees,
        head_relative_frame_forward: frameForward,
        head_relative_frame_target: frameTarget,
        left_eye_pivot_world: probe.leftPivotWorld,
        right_eye_pivot_world: probe.rightPivotWorld,
        left_eye_pivot_local: probe.leftPivotLocal,
        right_eye_pivot_local: probe.rightPivotLocal,
        left_eye_pivot_parent_basis: probe.leftPivotParentBasis,
        right_eye_pivot_parent_basis: probe.rightPivotParentBasis,
        left_eye_forward: probe.leftEyeForward,
        right_eye_forward: probe.rightEyeForward,
      };
    }
  }

  await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit), originalFit);
  await page.waitForTimeout(1_000);
  const finalProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const bodyHashAfter = sha256(BODY_PATH);
  const eyeHashAfter = sha256(EYE_PATH);
  const finalFit = finalProbe.runtimeVisualFit?.eyeGlobeTranslation || {};
  const fitKeys = [
    "forwardOffset", "verticalOffset", "horizontalOffset", "commonHorizontalOffset",
    "neutralYawDegrees", "irisHorizontalOffset", "irisVerticalOffset",
  ];
  const originalRestored = fitKeys.every((key) => Number(finalFit[key]) === Number(originalFit[key]));
  const checks = {
    exact_r6_body_hash_verified_before_and_after: bodyHashBefore === BODY_SHA256 && bodyHashAfter === BODY_SHA256,
    exact_eye_hash_verified_before_and_after: eyeHashBefore === EYE_SHA256 && eyeHashAfter === EYE_SHA256,
    eye_rig_structurally_complete: Boolean(finalProbe.active && finalProbe.structural?.complete),
    eye_rig_head_bound: Boolean(finalProbe.headBound),
    no_legacy_eye_nodes: finalProbe.oldProceduralNodeCount === 0,
    original_live_fit_restored: originalRestored,
    no_page_errors: diagnostics.page_errors.length === 0,
    no_console_errors: diagnostics.console_errors.length === 0,
  };
  evidence = {
    schema_version: 1,
    status: Object.values(checks).every(Boolean) ? "passed" : "failed",
    kind: "isolated_body_only_depth_sweep_no_ai_no_chat_no_voice_no_life_loop",
    exact_assets: {
      body: record(BODY_PATH),
      eye: record(EYE_PATH),
    },
    centered_geometry_fit_without_depth: CENTERED_GEOMETRY_FIT,
    review_base_fit_without_depth: REVIEW_BASE_FIT,
    tested_forward_offsets_metres: DEPTHS,
    tested_camera_yaw_degrees: CAMERA_YAWS,
    original_live_fit: originalFit,
    final_restored_fit: finalFit,
    head_forward_used_for_fixed_camera: headForward,
    socket_target_used_for_fixed_camera: target,
    screenshots,
    checks,
    diagnostics,
    conclusion: "This evidence varies only reversible runtime forward depth around the exact-R6 aperture-centred fit. It selects no winner automatically; original-resolution visual review is required, and the original live fit is restored before exit.",
  };
} finally {
  if (browser) await browser.close();
  if (assetServer) await new Promise((resolve) => assetServer.close(resolve));
  vite.kill("SIGTERM");
}

fs.writeFileSync(REPORT_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ evidence: record(REPORT_PATH), status: evidence.status, checks: evidence.checks }, null, 2));
if (evidence.status !== "passed") process.exitCode = 1;
