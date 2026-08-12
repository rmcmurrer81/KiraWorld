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
const EYE_SHA256 = "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413";
const REPORT_ROOT = path.join(ROOT, "Data", "world_tests", "kira_r6_head_relative_eye_multiview_20260721");
const REPORT_PATH = path.join(REPORT_ROOT, "evidence.json");

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

if (!fs.existsSync(BODY_PATH)) throw new Error(`Missing exact R6 body: ${BODY_PATH}`);
if (sha256(BODY_PATH) !== BODY_SHA256) throw new Error("Exact R6 body hash changed; refusing the eye-fit smoke.");
fs.mkdirSync(REPORT_ROOT, { recursive: true });

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
let evidence = { status: "failed", note: "The smoke did not finish." };

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
  // This injects only a body into an isolated browser smoke.  It starts no AI,
  // chat, life loop, voice process, or persistent world session.
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

  // Establish the head-relative forward direction with neutral eye yaw.  This
  // prevents the review camera from following the already-rotated iris/pivot.
  await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit({ ...fit, neutralYawDegrees: 0 }), originalFit);
  await page.waitForTimeout(900);
  const neutralProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const headForward = neutralProbe.leftEyeForward;
  if (!headForward) throw new Error("Could not establish the R6 head-relative forward direction.");

  await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit), originalFit);
  await page.waitForTimeout(900);
  const restoredProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const left = restoredProbe.leftSocketWorld;
  const right = restoredProbe.rightSocketWorld;
  if (!left || !right) throw new Error("Could not read both runtime eye-socket centres.");
  const target = {
    x: (left.x + right.x) * 0.5,
    y: (left.y + right.y) * 0.5,
    z: (left.z + right.z) * 0.5,
  };

  const views = [
    { id: "head_front", azimuth: 0 },
    { id: "head_left_three_quarter", azimuth: -30 },
    { id: "head_right_three_quarter", azimuth: 30 },
  ];
  const fitVariants = [
    { id: "current_yaw16", fit: originalFit },
    { id: "candidate_yaw0", fit: { ...originalFit, neutralYawDegrees: 0 } },
  ];
  const screenshots = {};
  for (const variant of fitVariants) {
    await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit), variant.fit);
    await page.waitForTimeout(900);
    screenshots[variant.id] = {};
    for (const view of views) {
      const direction = rotateAroundWorldY(headForward, view.azimuth);
      const distance = 0.34;
      const eye = {
        x: target.x + direction.x * distance,
        y: target.y + 0.003,
        z: target.z + direction.z * distance,
      };
      const dx = target.x - eye.x;
      const dz = target.z - eye.z;
      const dy = target.y - eye.y;
      const yaw = Math.atan2(-dx, -dz);
      const pitch = Math.atan2(dy, Math.max(0.001, Math.hypot(dx, dz)));
      await page.evaluate((camera) => window.kiraHomeWorldDebug.setPlayerPosition({ ...camera, floor: 0 }), {
        ...eye,
        yaw,
        pitch,
      });
      await page.waitForTimeout(350);
      const outputPath = path.join(REPORT_ROOT, `${variant.id}_${view.id}.png`);
      await page.screenshot({ path: outputPath });
      screenshots[variant.id][view.id] = {
        ...record(outputPath),
        neutral_yaw_degrees: Number(variant.fit.neutralYawDegrees),
        azimuth_degrees_about_head_forward: view.azimuth,
        camera: { ...eye, yaw, pitch },
      };
    }
  }

  await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit), originalFit);
  await page.waitForTimeout(900);
  const finalProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const finalBodyHash = sha256(BODY_PATH);
  const checks = {
    exact_r6_body_hash_verified: finalBodyHash === BODY_SHA256,
    exact_eye_hash_declared_by_runtime: finalProbe.expectedSha256 === EYE_SHA256,
    staged_eye_rig_structurally_active: Boolean(finalProbe.active && finalProbe.structural?.complete),
    eye_rig_bound_to_head: Boolean(finalProbe.headBound),
    no_legacy_eye_nodes: finalProbe.oldProceduralNodeCount === 0,
    original_fit_restored_after_head_axis_probe: Number(finalProbe.runtimeVisualFit?.eyeGlobeTranslation?.neutralYawDegrees) === Number(originalFit.neutralYawDegrees),
    no_page_errors: diagnostics.page_errors.length === 0,
    no_console_errors: diagnostics.console_errors.length === 0,
  };
  evidence = {
    status: Object.values(checks).every(Boolean) ? "passed" : "failed",
    kind: "isolated_body_only_browser_smoke_no_ai_no_chat_no_voice_no_life_loop",
    world_url: worldUrl,
    body: record(BODY_PATH),
    expected_body_sha256: BODY_SHA256,
    expected_eye_sha256: EYE_SHA256,
    original_fit: originalFit,
    neutral_head_axis_probe: neutralProbe,
    restored_runtime_probe: finalProbe,
    head_forward_used_for_all_views: headForward,
    checks,
    screenshots,
    diagnostics,
    conclusion: "Structural binding and source hashes pass, but eye seating remains a visual review question. These fixed head-relative front and +/-30 degree views compare the current +16-degree neutral yaw with a reversible 0-degree candidate without following the eye pivot or modifying either source GLB.",
  };
} finally {
  if (browser) await browser.close();
  if (assetServer) await new Promise((resolve) => assetServer.close(resolve));
  vite.kill("SIGTERM");
}

fs.writeFileSync(REPORT_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ evidence: record(REPORT_PATH), status: evidence.status, checks: evidence.checks, screenshots: evidence.screenshots }, null, 2));
if (evidence.status !== "passed") process.exitCode = 1;
