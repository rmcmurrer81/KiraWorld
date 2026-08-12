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
const MAIN_JS = path.join(PREVIEW_ROOT, "src", "main.js");
const PUBLIC_EYE = path.join(
  PREVIEW_ROOT, "public", "models", "home_world", "kira", "kira_brown_eye_rig_v3_2.glb",
);
const ORIGINAL_EYE = path.join(
  ROOT, "Avatar", "models", "staged", "kira", "eyes", "kira_brown_eye_rig_v3_2",
  "kira_brown_eye_rig_v3_2.glb",
);
const BODY_PATH = path.join(
  ROOT,
  "Avatar", "avatar_builder", "candidate_sources", "kira_provisional_body_r6",
  "r6_20260718_163658", "kira_provisional_body_r6.glb",
);
const DERIVED_EYE = process.env.KIRA_DERIVED_EYE_PATH
  ? path.resolve(ROOT, process.env.KIRA_DERIVED_EYE_PATH)
  : path.join(
      ROOT,
      "Avatar", "avatar_builder", "candidate_sources", "kira_r6_derived_eye_rig",
      "review_20260721", "r6_eye_s075_d070_f080.glb",
    );
const REPORT_ROOT = process.env.KIRA_DERIVED_EYE_REPORT_ROOT
  ? path.resolve(ROOT, process.env.KIRA_DERIVED_EYE_REPORT_ROOT)
  : path.join(ROOT, "Data", "world_tests", "kira_r6_derived_eye_asset_review_20260721");
const REPORT_PATH = path.join(REPORT_ROOT, "evidence.json");
const BODY_SHA256 = "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77";
const ORIGINAL_EYE_SHA256 = "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413";
const MAIN_JS_BASELINE_SHA256 = "56a763b0c235f63359b76c0aacdcbc74b222ad71043c8bb12bc7e4f055175b04";

const DEFAULT_REVIEW_FIT = Object.freeze({
  forwardOffset: 0,
  verticalOffset: 0.000004266304348021777,
  horizontalOffset: -0.00002159646739130147,
  commonHorizontalOffset: 0,
  neutralYawDegrees: 0,
  irisHorizontalOffset: 0,
  irisVerticalOffset: 0,
});
const REVIEW_FIT = Object.freeze({
  ...DEFAULT_REVIEW_FIT,
  ...(process.env.KIRA_DERIVED_EYE_REVIEW_FIT_JSON
    ? JSON.parse(process.env.KIRA_DERIVED_EYE_REVIEW_FIT_JSON)
    : {}),
});
const REVIEW_VISUAL_DECISION = process.env.KIRA_DERIVED_EYE_VISUAL_DECISION_JSON
  ? JSON.parse(process.env.KIRA_DERIVED_EYE_VISUAL_DECISION_JSON)
  : null;

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

if (!fs.existsSync(DERIVED_EYE)) throw new Error(`Derived eye candidate is missing: ${DERIVED_EYE}`);
if (sha256(BODY_PATH) !== BODY_SHA256) throw new Error("Exact R6 body hash changed; refusing review.");
if (sha256(ORIGINAL_EYE) !== ORIGINAL_EYE_SHA256) throw new Error("Original eye source hash changed; refusing review.");
if (sha256(PUBLIC_EYE) !== ORIGINAL_EYE_SHA256) throw new Error("Public live eye asset differs from the preserved original; refusing review.");
if (sha256(MAIN_JS) !== MAIN_JS_BASELINE_SHA256) throw new Error("Home World main.js differs from the restored baseline; refusing review.");
fs.mkdirSync(REPORT_ROOT, { recursive: true });

const hashesBefore = {
  body: sha256(BODY_PATH),
  original_eye: sha256(ORIGINAL_EYE),
  public_eye: sha256(PUBLIC_EYE),
  main_js: sha256(MAIN_JS),
};
const vitePort = await freePort();
const assetPort = await freePort();
const worldUrl = `http://127.0.0.1:${vitePort}/?area=home&motionSmoke=1&kiraEyeIdleFit=off`;
const bodyRelative = path.relative(ROOT, BODY_PATH).replaceAll("\\", "/");
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
let evidence = { status: "failed", note: "Derived-eye review did not finish." };

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

  // Route only this isolated browser's staged-eye request to the derived GLB.
  // No public/live file is copied, renamed, edited, or replaced on disk.
  let derivedRouteCount = 0;
  await page.route("**/models/home_world/kira/kira_brown_eye_rig_v3_2.glb", async (route) => {
    derivedRouteCount += 1;
    await route.fulfill({
      status: 200,
      contentType: "model/gltf-binary",
      headers: { "Cache-Control": "no-store" },
      body: fs.readFileSync(DERIVED_EYE),
    });
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
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.activeAvatarState?.().rootPresent), null, { timeout: 120_000 });
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.kiraEyeRig?.()?.active), null, { timeout: 30_000 });
  await page.evaluate((fit) => {
    window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit);
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 0);
  }, REVIEW_FIT);
  await page.waitForTimeout(1_000);

  async function positionCamera(cameraYawDegrees) {
    const probe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
    const forward = probe.leftPivotParentBasis?.localZInWorld || probe.leftEyeForward;
    const left = probe.leftSocketWorld;
    const right = probe.rightSocketWorld;
    if (!forward || !left || !right) throw new Error("Could not read the head-relative eye frame.");
    const target = {
      x: (left.x + right.x) * 0.5,
      y: (left.y + right.y) * 0.5,
      z: (left.z + right.z) * 0.5,
    };
    const direction = rotateAroundWorldY(forward, cameraYawDegrees);
    const distance = 0.34;
    const eye = {
      x: target.x + direction.x * distance,
      y: target.y + 0.003,
      z: target.z + direction.z * distance,
    };
    const dx = target.x - eye.x;
    const dz = target.z - eye.z;
    const dy = target.y - eye.y;
    await page.evaluate((camera) => window.kiraHomeWorldDebug.setPlayerPosition({ ...camera, floor: 0 }), {
      ...eye,
      yaw: Math.atan2(-dx, -dz),
      pitch: Math.atan2(dy, Math.max(0.001, Math.hypot(dx, dz))),
    });
    await page.waitForTimeout(80);
    return { forward, target, eye };
  }

  async function capture(id, cameraYawDegrees, direction = "center", blink = 0) {
    await page.evaluate(({ direction: requestedDirection, blink: requestedBlink }) => {
      window.kiraHomeWorldDebug.setKiraEyeDirection(requestedDirection);
      window.kiraHomeWorldDebug.setKiraEyeBlink("both", requestedBlink);
    }, { direction, blink });
    await page.waitForTimeout(250);
    const frame = await positionCamera(cameraYawDegrees);
    const outputPath = path.join(REPORT_ROOT, `${id}.png`);
    await page.screenshot({ path: outputPath });
    return {
      ...record(outputPath),
      camera_yaw_degrees: cameraYawDegrees,
      direction,
      blink,
      frame,
      probe: await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig()),
    };
  }

  const screenshots = {
    neutral_front: await capture("neutral_front", 0),
    neutral_left_30deg: await capture("neutral_left_30deg", -30),
    neutral_right_30deg: await capture("neutral_right_30deg", 30),
    blink_closed_front: await capture("blink_closed_front", 0, "center", 1),
    gaze_left_front: await capture("gaze_left_front", 0, "left", 0),
    gaze_right_front: await capture("gaze_right_front", 0, "right", 0),
  };

  const finalProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const hashesAfter = {
    body: sha256(BODY_PATH),
    original_eye: sha256(ORIGINAL_EYE),
    public_eye: sha256(PUBLIC_EYE),
    main_js: sha256(MAIN_JS),
  };
  const checks = {
    exact_r6_body_unchanged: hashesBefore.body === BODY_SHA256 && hashesAfter.body === BODY_SHA256,
    original_eye_unchanged: hashesBefore.original_eye === ORIGINAL_EYE_SHA256 && hashesAfter.original_eye === ORIGINAL_EYE_SHA256,
    public_live_eye_unchanged: hashesBefore.public_eye === ORIGINAL_EYE_SHA256 && hashesAfter.public_eye === ORIGINAL_EYE_SHA256,
    runtime_main_js_unchanged: hashesBefore.main_js === MAIN_JS_BASELINE_SHA256 && hashesAfter.main_js === MAIN_JS_BASELINE_SHA256,
    derived_asset_intercepted_in_isolated_page: derivedRouteCount >= 1,
    eye_rig_structurally_complete: Boolean(finalProbe.active && finalProbe.structural?.complete),
    eye_rig_head_bound: Boolean(finalProbe.headBound),
    no_legacy_eye_nodes: finalProbe.oldProceduralNodeCount === 0,
    no_page_errors: diagnostics.page_errors.length === 0,
    no_console_errors: diagnostics.console_errors.length === 0,
  };
  const structuralPassed = Object.values(checks).every(Boolean);
  const visualAcceptance = {
    both_irises_centered_and_visible_front: null,
    both_irises_visible_left_30deg: null,
    both_irises_visible_right_30deg: null,
    no_globe_or_temple_protrusion: null,
    plausible_closed_blink: null,
    plausible_left_and_right_gaze_clearance: null,
    ...(REVIEW_VISUAL_DECISION || {}),
    // This harness is deliberately review-only and cannot promote an asset.
    promotion_allowed: false,
    note: REVIEW_VISUAL_DECISION
      ? "Recorded human visual review. A rejected criterion keeps this derived asset inactive and blocks promotion."
      : "Null visual fields require original-resolution human review. Structural pass never authorizes promotion.",
  };
  const visualRejected = REVIEW_VISUAL_DECISION
    ? [
        "both_irises_centered_and_visible_front",
        "both_irises_visible_left_30deg",
        "both_irises_visible_right_30deg",
        "no_globe_or_temple_protrusion",
        "plausible_closed_blink",
        "plausible_left_and_right_gaze_clearance",
      ].some((key) => visualAcceptance[key] === false)
    : false;
  evidence = {
    schema_version: 1,
    status: !structuralPassed
      ? "failed"
      : visualRejected
        ? "rejected_visual_fit"
        : "structural_review_complete_visual_decision_pending",
    kind: "isolated_browser_route_inactive_derived_eye_asset_no_file_swap_no_ai_no_chat_no_voice_no_life_loop",
    exact_assets: {
      body: record(BODY_PATH),
      original_eye: record(ORIGINAL_EYE),
      public_live_eye: record(PUBLIC_EYE),
      derived_eye: record(DERIVED_EYE),
      main_js: record(MAIN_JS),
    },
    review_fit: REVIEW_FIT,
    route: {
      request_pattern: "**/models/home_world/kira/kira_brown_eye_rig_v3_2.glb",
      derived_route_count: derivedRouteCount,
      disk_public_asset_replaced: false,
    },
    hashes_before: hashesBefore,
    hashes_after: hashesAfter,
    screenshots,
    checks,
    diagnostics,
    visual_acceptance: visualAcceptance,
  };
} finally {
  if (browser) await browser.close();
  if (assetServer) await new Promise((resolve) => assetServer.close(resolve));
  vite.kill("SIGTERM");
}

fs.writeFileSync(REPORT_PATH, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ evidence: record(REPORT_PATH), status: evidence.status, checks: evidence.checks }, null, 2));
if (evidence.status === "failed") process.exitCode = 1;
