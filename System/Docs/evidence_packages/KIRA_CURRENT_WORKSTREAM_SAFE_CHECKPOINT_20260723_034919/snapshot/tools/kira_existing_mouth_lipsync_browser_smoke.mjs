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
const DEFAULT_R6_BODY_PATH = path.join(
  ROOT,
  "Avatar", "avatar_builder", "candidate_sources", "kira_provisional_body_r6",
  "r6_20260718_163658", "kira_provisional_body_r6.glb",
);
const EXPECTED_R6_SHA256 = "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77";
const BODY_PATH = process.env.KIRA_BODY_PATH
  ? path.resolve(ROOT, process.env.KIRA_BODY_PATH)
  : DEFAULT_R6_BODY_PATH;
const optionalNumber = (name) => process.env[name] === undefined ? undefined : Number(process.env[name]);
const EYE_FIT_OVERRIDE = [
  "KIRA_EYE_FORWARD_OFFSET", "KIRA_EYE_VERTICAL_OFFSET", "KIRA_EYE_HORIZONTAL_OFFSET", "KIRA_EYE_COMMON_HORIZONTAL_OFFSET", "KIRA_EYE_NEUTRAL_YAW_DEGREES",
  "KIRA_IRIS_HORIZONTAL_OFFSET", "KIRA_IRIS_VERTICAL_OFFSET",
]
  .some((name) => process.env[name] !== undefined)
  ? {
      forwardOffset: optionalNumber("KIRA_EYE_FORWARD_OFFSET"),
      verticalOffset: optionalNumber("KIRA_EYE_VERTICAL_OFFSET"),
      horizontalOffset: optionalNumber("KIRA_EYE_HORIZONTAL_OFFSET"),
      commonHorizontalOffset: optionalNumber("KIRA_EYE_COMMON_HORIZONTAL_OFFSET"),
      neutralYawDegrees: optionalNumber("KIRA_EYE_NEUTRAL_YAW_DEGREES"),
      irisHorizontalOffset: optionalNumber("KIRA_IRIS_HORIZONTAL_OFFSET"),
      irisVerticalOffset: optionalNumber("KIRA_IRIS_VERTICAL_OFFSET"),
    }
  : null;
const REPORT_ROOT = process.env.KIRA_FACE_REPORT_ROOT
  ? path.resolve(ROOT, process.env.KIRA_FACE_REPORT_ROOT)
  : path.join(ROOT, "Data", "world_tests", "kira_r6_face_motion_runtime_20260718");
const REPORT_PATH = path.join(REPORT_ROOT, "browser_smoke.json");
const CLOSED_SCREENSHOT_PATH = path.join(REPORT_ROOT, "existing_mouth_closed.png");
const MID_SCREENSHOT_PATH = path.join(REPORT_ROOT, "existing_mouth_mid_playback.png");
const OPEN_SCREENSHOT_PATH = path.join(REPORT_ROOT, "existing_mouth_actual_playback.png");
const RESTORED_SCREENSHOT_PATH = path.join(REPORT_ROOT, "existing_mouth_restored.png");
const CLOSED_CLOSEUP_PATH = path.join(REPORT_ROOT, "existing_mouth_closed_closeup.png");
const MID_CLOSEUP_PATH = path.join(REPORT_ROOT, "existing_mouth_mid_playback_closeup.png");
const OPEN_CLOSEUP_PATH = path.join(REPORT_ROOT, "existing_mouth_actual_playback_closeup.png");
const RESTORED_CLOSEUP_PATH = path.join(REPORT_ROOT, "existing_mouth_restored_closeup.png");

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function normalizedPixelDifference(left, right) {
  const count = Math.min(left?.pixels?.length || 0, right?.pixels?.length || 0);
  if (!count) return 0;
  let difference = 0;
  let channels = 0;
  for (let index = 0; index < count; index += 4) {
    difference += Math.abs(left.pixels[index] - right.pixels[index]);
    difference += Math.abs(left.pixels[index + 1] - right.pixels[index + 1]);
    difference += Math.abs(left.pixels[index + 2] - right.pixels[index + 2]);
    channels += 3;
  }
  return difference / Math.max(1, channels * 255);
}

function jointRotationDifference(left, right, names) {
  let total = 0;
  for (const name of names) {
    for (const axis of ["x", "y", "z"]) {
      total += Math.abs(Number(left?.joints?.[name]?.[axis] || 0) - Number(right?.joints?.[name]?.[axis] || 0));
    }
  }
  return total;
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

if (!fs.existsSync(BODY_PATH)) throw new Error(`Missing Kira body: ${BODY_PATH}`);
fs.mkdirSync(REPORT_ROOT, { recursive: true });
const bodyHashBefore = sha256(BODY_PATH);
const bodyRelativePath = path.relative(ROOT, BODY_PATH).replaceAll("\\", "/");
const vitePort = await freePort();
const assetPort = await freePort();
// Disable autonomous idle eye drift for the evidence frames.  The screenshots
// must prove the neutral authored centre, not a random saccade sample.
const worldUrl = `http://127.0.0.1:${vitePort}/?area=home&motionSmoke=1&kiraEyeIdleFit=off`;
const bodyUrl = `http://127.0.0.1:${assetPort}/${bodyRelativePath}?v=${fs.statSync(BODY_PATH).mtimeMs}`;
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
  await page.waitForTimeout(1_000);
  const attachmentProbe = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  if (!attachmentProbe.active) {
    throw new Error(`Live Kira mouth rig did not attach: ${JSON.stringify({ attachmentProbe, diagnostics }, null, 2)}`);
  }

  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.kiraEyeRig?.()?.active), null, { timeout: 30_000 });
  if (EYE_FIT_OVERRIDE) {
    await page.evaluate((fit) => window.kiraHomeWorldDebug.setKiraR6EyeVisualFit(fit), EYE_FIT_OVERRIDE);
  }
  await page.evaluate(() => {
    window.kiraHomeWorldDebug.setKiraEyeDirection("center");
    window.kiraHomeWorldDebug.setKiraEyeBlink("both", 0);
    window.kiraHomeWorldDebug.focusKiraEyes({ distance: 0.29, y: -0.01 });
  });
  await page.waitForTimeout(600);

  const sampleMouthPixels = () => page.evaluate(() => {
    const bounds = window.kiraHomeWorldDebug.kiraExistingMouthScreenBounds();
    const source = document.querySelector("canvas");
    if (!bounds || !source) return { bounds, pixels: [] };
    const canvasRect = source.getBoundingClientRect();
    const padX = Math.max(10, bounds.width * 0.75);
    const padY = Math.max(8, bounds.height * 2.2);
    const sourceX = Math.max(0, Math.floor(bounds.minX - canvasRect.left - padX));
    const sourceY = Math.max(0, Math.floor(bounds.minY - canvasRect.top - padY));
    const sourceWidth = Math.min(source.width - sourceX, Math.ceil(bounds.width + padX * 2));
    const sourceHeight = Math.min(source.height - sourceY, Math.ceil(bounds.height + padY * 2));
    const normalized = document.createElement("canvas");
    normalized.width = 128;
    normalized.height = 96;
    const context = normalized.getContext("2d", { willReadFrequently: true });
    context.drawImage(source, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, normalized.width, normalized.height);
    return {
      bounds,
      crop: { sourceX, sourceY, sourceWidth, sourceHeight, width: normalized.width, height: normalized.height },
      pixels: Array.from(context.getImageData(0, 0, normalized.width, normalized.height).data),
    };
  });

  const screenshotMouthCloseup = async (outputPath) => {
    const bounds = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthScreenBounds());
    if (!bounds) throw new Error("Cannot capture mouth close-up without projected existing-lip bounds.");
    const viewport = page.viewportSize();
    const targetWidth = Math.min(viewport.width, Math.max(360, bounds.width * 4.5));
    const targetHeight = Math.min(viewport.height, Math.max(220, bounds.height * 8));
    const x = Math.max(0, Math.min(viewport.width - targetWidth, bounds.centerX - targetWidth * 0.5));
    const y = Math.max(0, Math.min(viewport.height - targetHeight, bounds.centerY - targetHeight * 0.5));
    await page.screenshot({
      path: outputPath,
      clip: { x, y, width: targetWidth, height: targetHeight },
    });
    return { x, y, width: targetWidth, height: targetHeight };
  };

  const closedBefore = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  const closedPixels = await sampleMouthPixels();
  await page.screenshot({ path: CLOSED_SCREENSHOT_PATH });
  const closedCloseupClip = await screenshotMouthCloseup(CLOSED_CLOSEUP_PATH);
  const injectedStart = await page.evaluate(() => window.kiraHomeWorldDebug.injectVoicePlaybackForHeadlessTest({
    revision: 1,
    active: true,
    playing: true,
    phase: "chunk_playback",
    candidate: "kira",
    label: "Kira",
    chunk_index: 0,
    playback_started_at: Date.now() / 1000,
  }));
  await page.waitForFunction(() => {
    const probe = window.kiraHomeWorldDebug?.kiraExistingMouthLipSync?.();
    return Boolean(probe?.playingMatchedActiveAvatar && probe?.amount >= 0.35 && probe?.amount <= 0.68);
  }, null, { timeout: 10_000 });
  const midPlaying = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  const midPixels = await sampleMouthPixels();
  await page.screenshot({ path: MID_SCREENSHOT_PATH });
  const midCloseupClip = await screenshotMouthCloseup(MID_CLOSEUP_PATH);
  await page.waitForFunction(() => {
    const probe = window.kiraHomeWorldDebug?.kiraExistingMouthLipSync?.();
    return Boolean(probe?.playingMatchedActiveAvatar && probe?.amount > 0.82 && probe?.maximumSeamDisplacement > 0.001);
  }, null, { timeout: 10_000 });
  const whilePlaying = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  const playingStateOne = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const eyeRigWhilePlaying = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeRig());
  const openPixels = await sampleMouthPixels();
  await page.screenshot({ path: OPEN_SCREENSHOT_PATH });
  const openCloseupClip = await screenshotMouthCloseup(OPEN_CLOSEUP_PATH);
  await page.waitForTimeout(850);
  const playingStateTwo = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());

  const injectedStop = await page.evaluate(() => window.kiraHomeWorldDebug.injectVoicePlaybackForHeadlessTest({
    revision: 2,
    active: true,
    playing: false,
    phase: "chunk_playback_end",
    candidate: "kira",
    label: "Kira",
    chunk_index: 0,
    playback_ended_at: Date.now() / 1000,
  }));
  await page.waitForFunction(() => {
    const probe = window.kiraHomeWorldDebug?.kiraExistingMouthLipSync?.();
    return Boolean(probe?.active && probe?.restored && probe?.amount === 0 && !probe?.playingMatchedActiveAvatar);
  }, null, { timeout: 10_000 });
  const closedAfter = await page.evaluate(() => window.kiraHomeWorldDebug.kiraExistingMouthLipSync());
  await page.waitForFunction(() => window.kiraHomeWorldDebug?.activeAvatarState?.().action === "idle", null, { timeout: 10_000 });
  const restoredState = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  await page.screenshot({ path: RESTORED_SCREENSHOT_PATH });
  const restoredCloseupClip = await screenshotMouthCloseup(RESTORED_CLOSEUP_PATH);
  const eyeSocketFit = await page.evaluate(() => window.kiraHomeWorldDebug.kiraEyeSocketFit());
  const bodyHashAfter = sha256(BODY_PATH);
  const visiblePixelDifference = normalizedPixelDifference(closedPixels, openPixels);
  const midProjectedMouthHeightIncrease = Number(midPixels.bounds?.height || 0) - Number(closedPixels.bounds?.height || 0);
  const projectedMouthHeightIncrease = Number(openPixels.bounds?.height || 0) - Number(closedPixels.bounds?.height || 0);
  const expressionJointDifference = jointRotationDifference(
    playingStateOne.comfortIdle,
    playingStateTwo.comfortIdle,
    ["leftUpperArm", "leftForearm", "leftHand", "rightUpperArm", "rightForearm", "rightHand"],
  );

  const activeAvatarState = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const checks = {
    exact_r6_body_sha_loaded: bodyHashBefore === EXPECTED_R6_SHA256,
    exact_r6_body_url_loaded: String(activeAvatarState?.modelUrl || "").startsWith(bodyUrl),
    exact_r6_existing_lip_island_selected: closedBefore.active && closedBefore.vertexCount >= 40,
    actual_playback_start_deforms_existing_lip_surface: injectedStart.accepted
      && whilePlaying.playingMatchedActiveAvatar
      && whilePlaying.amount > 0.55
      && whilePlaying.openingDistance >= 0.004
      && whilePlaying.openingDistance <= 0.010
      && whilePlaying.maximumSeamDisplacement > 0.001
      && whilePlaying.maximumPerimeterDisplacement <= 0.00005
      && projectedMouthHeightIncrease >= 4
      && projectedMouthHeightIncrease <= 40,
    existing_lip_deformation_has_projected_screen_amplitude: whilePlaying.existingVertexColorSpeechShading
      && whilePlaying.innerLipShadeAmount > 0.15
      && projectedMouthHeightIncrease >= 4
      && projectedMouthHeightIncrease <= 40,
    playback_end_restores_existing_lips: injectedStop.accepted && closedAfter.restored && closedAfter.amount === 0,
    no_second_mouth_mesh: closedBefore.secondMouthCreated === false
      && closedBefore.createdSceneNodes === 0
      && closedBefore.meshCountBefore === closedBefore.meshCountAfter,
    existing_mouth_only_no_replacement_geometry: closedBefore.method === "in_place_existing_position_attribute_bounded_seam_deformation_plus_anchored_perimeter_tint",
    actual_playback_owns_talking_expression_then_releases: playingStateOne.action === "talking"
      && playingStateOne.comfortIdle?.actualPlaybackExpression === true
      && restoredState.action === "idle",
    arms_hands_change_during_actual_playback_expression: expressionJointDifference > 0.01,
    eye_runtime_fit_is_reversible_r6_visual_placement: eyeRigWhilePlaying?.runtimeVisualFit?.irisLimbusPupilDiameterScale === 1.08
      && eyeRigWhilePlaying?.runtimeVisualFit?.corneaDiameterScale === 1
      && eyeRigWhilePlaying?.runtimeVisualFit?.r6VisualPlacementApplied === true
      && eyeRigWhilePlaying?.runtimeVisualFit?.eyeGlobeTranslationApplied === true
      && eyeRigWhilePlaying?.runtimeVisualFit?.eyeGlobeTranslation?.neutralYawDegrees === 16
      && eyeRigWhilePlaying?.direction === "center",
    live_body_asset_unchanged: bodyHashBefore === bodyHashAfter,
    no_page_errors: diagnostics.page_errors.length === 0,
  };
  const technicalPass = Object.values(checks).every(Boolean);
  const report = {
    schema_version: 3,
    generated_at: new Date().toISOString(),
    status: technicalPass ? "technical_pass_pending_original_resolution_visual_review" : "failed_or_incomplete",
    visual_review: {
      status: "pending_original_resolution_review",
      note: "Geometry telemetry and projected bounds are not visual proof. R6 has no facial bones or viseme morph targets, so this report proves only playback-driven deformation of the existing lip surface. Inspect all four saved PNG files at original resolution before acceptance; do not call it working lip sync until that review passes.",
      idle_saccades_disabled: true,
    },
    isolation: {
      live_person_activated: false,
      life_loop_started: false,
      shell_state_persisted: false,
      mode: "isolated headless motionSmoke renderer",
    },
    asset: {
      path: bodyRelativePath,
      expected_r6_sha256: EXPECTED_R6_SHA256,
      sha256_before: bodyHashBefore,
      sha256_after: bodyHashAfter,
      renderer_model_url: activeAvatarState?.modelUrl || "",
    },
    checks,
    closed_before: closedBefore,
    mid_playing: midPlaying,
    while_playing: whilePlaying,
    closed_after: closedAfter,
    visible_pixel_difference: Number(visiblePixelDifference.toFixed(8)),
    visible_pixel_readback_note: visiblePixelDifference === 0
      ? "WebGL back-buffer drawImage readback was unavailable; use the saved screenshots and projected existing-lip bounds instead."
      : "normalized RGB difference from the WebGL mouth crop",
    projected_existing_lip_mid_height_increase_pixels: Number(midProjectedMouthHeightIncrease.toFixed(4)),
    projected_existing_lip_height_increase_pixels: Number(projectedMouthHeightIncrease.toFixed(4)),
    expression_joint_difference_radians: Number(expressionJointDifference.toFixed(8)),
    mouth_pixel_crops: {
      closed: { bounds: closedPixels.bounds, crop: closedPixels.crop },
      mid_playback: { bounds: midPixels.bounds, crop: midPixels.crop },
      actual_playback: { bounds: openPixels.bounds, crop: openPixels.crop },
    },
    expression_states: {
      actual_playback_first: playingStateOne.comfortIdle,
      actual_playback_second: playingStateTwo.comfortIdle,
      restored_action: restoredState.action,
    },
    eye_rig_while_playing: eyeRigWhilePlaying,
    eye_socket_fit: eyeSocketFit,
    screenshots: {
      closed: path.relative(ROOT, CLOSED_SCREENSHOT_PATH).replaceAll("\\", "/"),
      mid_playback: path.relative(ROOT, MID_SCREENSHOT_PATH).replaceAll("\\", "/"),
      actual_playback: path.relative(ROOT, OPEN_SCREENSHOT_PATH).replaceAll("\\", "/"),
      restored: path.relative(ROOT, RESTORED_SCREENSHOT_PATH).replaceAll("\\", "/"),
      closeups: {
        closed: path.relative(ROOT, CLOSED_CLOSEUP_PATH).replaceAll("\\", "/"),
        mid_playback: path.relative(ROOT, MID_CLOSEUP_PATH).replaceAll("\\", "/"),
        actual_playback: path.relative(ROOT, OPEN_CLOSEUP_PATH).replaceAll("\\", "/"),
        restored: path.relative(ROOT, RESTORED_CLOSEUP_PATH).replaceAll("\\", "/"),
      },
      closeup_clips: {
        closed: closedCloseupClip,
        mid_playback: midCloseupClip,
        actual_playback: openCloseupClip,
        restored: restoredCloseupClip,
      },
    },
    diagnostics,
    vite_output_tail: viteOutput,
  };
  fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: report.status, checks, visiblePixelDifference, projectedMouthHeightIncrease, expressionJointDifference, closedBefore, whilePlaying, closedAfter, eyeRigWhilePlaying, diagnostics }, null, 2)}\n`);
  if (!technicalPass) process.exitCode = 1;
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
