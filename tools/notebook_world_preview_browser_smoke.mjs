import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

function option(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

function requireValue(name) {
  const value = option(name);
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const url = requireValue("--url");
const reportPath = requireValue("--report");
const screenshotPath = requireValue("--screenshot");
const cameraDir = option("--camera-dir", "");
const expectedWorld = requireValue("--expected-world");
const expectedBuild = requireValue("--expected-build");
const expectedRooms = Number(option("--expected-rooms", "2"));
const diagnostics = { page_errors: [], console_errors: [], request_failures: [], http_errors: [] };
let browser;
let report = {
  schema_version: 1,
  status: "failed",
  url,
  expected_world_id: expectedWorld,
  expected_build_id: expectedBuild,
  diagnostics,
};

function recordDiagnostics(page) {
  page.on("pageerror", (error) => diagnostics.page_errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.console_errors.push(message.text());
  });
  page.on("requestfailed", (request) => {
    diagnostics.request_failures.push(`${request.url()} :: ${request.failure()?.errorText || "failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) diagnostics.http_errors.push(`${response.status()} ${response.url()}`);
  });
}

async function sampleFramesAndPixels(page) {
  return page.evaluate(async () => {
    const canvas = document.querySelector("canvas");
    if (!canvas) return { canvas: null, frames: 0, pixel_sample: null };
    let frames = 0;
    await new Promise((resolve) => {
      const start = performance.now();
      function tick(now) {
        frames += 1;
        if (now - start >= 1000) resolve();
        else requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    let pixelSample = null;
    if (gl && canvas.width > 0 && canvas.height > 0) {
      const pixels = new Uint8Array(canvas.width * canvas.height * 4);
      gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      const colors = new Set();
      let opaque = 0;
      const stridePixels = Math.max(1, Math.floor((canvas.width * canvas.height) / 2048));
      for (let pixelIndex = 0; pixelIndex < canvas.width * canvas.height; pixelIndex += stridePixels) {
        const index = pixelIndex * 4;
        colors.add(`${pixels[index]},${pixels[index + 1]},${pixels[index + 2]},${pixels[index + 3]}`);
        if (pixels[index + 3] > 0) opaque += 1;
      }
      pixelSample = { unique_rgba_samples: colors.size, opaque_samples: opaque };
    }
    return {
      canvas: { width: canvas.width, height: canvas.height },
      frames,
      pixel_sample: pixelSample,
    };
  });
}

async function settledScreenshot(page, targetPath, selector = "") {
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.waitForTimeout(180);
  const panelReady = await page.locator(".review-panel").evaluate((panel) => (
    panel.innerText.includes("Generated scene contract") && panel.innerText.includes("Rooms and build scope")
  ));
  assert(panelReady, "Evidence sidebar was not populated before screenshot capture");
  // Warm the compositor once. Continuous WebGL frames can otherwise race a
  // first headless full-window capture and leave an unrelated DOM tile black.
  await page.screenshot();
  await page.waitForTimeout(80);
  return selector
    ? page.locator(selector).screenshot({ path: targetPath })
    : page.screenshot({ path: targetPath });
}

try {
  const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const launchOptions = {
    headless: true,
    args: ["--use-angle=default", "--enable-webgl", "--disable-background-timer-throttling"],
  };
  if (process.platform === "win32" && fs.existsSync(edge)) launchOptions.executablePath = edge;
  browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  recordDiagnostics(page);
  await page.goto(url, { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForFunction(() => window.__previewReady === true, null, { timeout: 120000 });

  const state = await page.evaluate(async () => {
    const metadata = await fetch("/data/scene_manifest.json", { cache: "no-store" }).then((response) => response.json());
    const debug = window.__notebookWorldDebug;
    const routeChecks = debug.runStaticRouteChecks();
    const cameraResults = metadata.cameras.map((camera) => ({ id: camera.id, selected: debug.setCamera(camera.id) }));
    const screenshotCamera = metadata.cameras[Math.min(1, metadata.cameras.length - 1)] || null;
    const blockedWall = debug.blocked(-9, 0);
    const clearExterior = debug.blocked(0, 8);
    const blockedMoveAccepted = debug.setWalkPosition(-9, 0);
    const safeMoveAccepted = debug.setWalkPosition(0, 8);
    if (screenshotCamera) debug.setCamera(screenshotCamera.id);
    return {
      world_id: metadata.world_id,
      build_id: debug.buildId,
      status: debug.status,
      home_world_mutation_allowed: debug.homeWorldMutationAllowed,
      strip_mall_mutation_allowed: debug.stripMallMutationAllowed,
      runtime_registered: debug.runtimeRegistered,
      people_loaded: debug.peopleLoaded,
      minds_loaded: debug.mindsLoaded,
      voice_loaded: debug.voiceLoaded,
      room_count: debug.roomCount,
      rooms: debug.rooms,
      primitive_count: debug.primitiveCount,
      collider_count: debug.colliderCount,
      route_count: debug.routeCount,
      spawn_count: debug.spawnCount,
      camera_count: debug.cameraCount,
      filming_mark_count: debug.filmingMarkCount,
      route_checks: routeChecks,
      camera_results: cameraResults,
      screenshot_camera_id: screenshotCamera?.id || null,
      collision_probes: { blocked_wall: blockedWall, clear_exterior: clearExterior },
      movement_probes: { blocked_move_accepted: blockedMoveAccepted, safe_move_accepted: safeMoveAccepted },
      overlay_cards: document.querySelectorAll(".overlay-card").length,
      truth_chips: document.querySelectorAll(".truth-chip").length,
      visible_status: document.getElementById("runtime-status")?.textContent || "",
      snapshot: debug.getSnapshot(),
    };
  });

  const cameraScreenshots = [];
  if (cameraDir) {
    fs.mkdirSync(cameraDir, { recursive: true });
    for (const cameraResult of state.camera_results) {
      await page.evaluate((cameraId) => window.__notebookWorldDebug.setCamera(cameraId), cameraResult.id);
      await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const cameraPath = path.join(cameraDir, `${cameraResult.id}.png`);
      const cameraShot = await settledScreenshot(page, cameraPath, ".viewport-shell");
      cameraScreenshots.push({
        camera_id: cameraResult.id,
        path: cameraPath,
        bytes: cameraShot.length,
        sha256: crypto.createHash("sha256").update(cameraShot).digest("hex"),
      });
    }
    await page.evaluate((cameraId) => window.__notebookWorldDebug.setCamera(cameraId), state.screenshot_camera_id);
  }

  const renderSample = await sampleFramesAndPixels(page);
  fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
  const screenshot = await settledScreenshot(page, screenshotPath, ".viewport-shell");
  const screenshotSha256 = crypto.createHash("sha256").update(screenshot).digest("hex");
  const panelPath = path.join(
    path.dirname(screenshotPath),
    `${path.basename(screenshotPath, path.extname(screenshotPath))}_evidence_panel.png`,
  );
  const panelScreenshot = await settledScreenshot(page, panelPath, ".review-panel");
  const panelScreenshotSha256 = crypto.createHash("sha256").update(panelScreenshot).digest("hex");

  assert(state.world_id === expectedWorld, "Headless scene world id diverges");
  assert(state.build_id === expectedBuild, "Headless scene build id diverges");
  assert(state.status === "prototype_draft_not_final_not_approved", "Headless scene claims an unsupported status");
  assert(state.room_count === expectedRooms, `Expected ${expectedRooms} rooms, got ${state.room_count}`);
  assert(state.rooms.length === expectedRooms, "Room identifiers are incomplete");
  assert(state.home_world_mutation_allowed === false, "Home World mutation became allowed");
  assert(state.strip_mall_mutation_allowed === false, "Strip-mall mutation became allowed");
  assert(state.runtime_registered === false, "Draft runtime became registered");
  assert(state.people_loaded === 0 && state.minds_loaded === 0 && state.voice_loaded === false, "A person, mind, or voice was loaded");
  assert(state.primitive_count > 0 && state.collider_count > 0, "Procedural geometry or collision metadata is empty");
  assert(state.spawn_count === 3 && state.filming_mark_count === 6, "Future empty marks diverged");
  assert(state.route_checks.length === state.route_count, "Route check count diverges");
  assert(state.route_checks.every((item) => item.status === "clear"), "A static route is obstructed");
  assert(state.camera_results.every((item) => item.selected), "A declared camera preset could not be selected");
  assert(state.collision_probes.blocked_wall === true && state.collision_probes.clear_exterior === false, "Collider probes failed");
  assert(state.movement_probes.blocked_move_accepted === false && state.movement_probes.safe_move_accepted === true, "Walk-position fail-closed probes failed");
  assert(state.overlay_cards === 2 && state.truth_chips >= 3, "Builder overlays or truth labels are not rendered");
  assert(renderSample.canvas?.width > 0 && renderSample.canvas?.height > 0 && renderSample.frames > 0, "Three.js canvas did not render frames");
  assert(renderSample.pixel_sample?.unique_rgba_samples > 2, "Rendered canvas lacks visible color variation");
  assert(screenshot.length > 10000, "Headless screenshot is unexpectedly empty");
  assert(panelScreenshot.length > 10000, "Evidence-sidebar screenshot is unexpectedly empty");
  assert(diagnostics.page_errors.length === 0, `Page errors: ${diagnostics.page_errors.join(" | ")}`);
  assert(diagnostics.console_errors.length === 0, `Console errors: ${diagnostics.console_errors.join(" | ")}`);
  assert(diagnostics.request_failures.length === 0, `Request failures: ${diagnostics.request_failures.join(" | ")}`);
  assert(diagnostics.http_errors.length === 0, `HTTP errors: ${diagnostics.http_errors.join(" | ")}`);

  report = {
    ...report,
    status: "passed",
    state,
    render_sample: renderSample,
    screenshot: {
      path: screenshotPath,
      bytes: screenshot.length,
      sha256: screenshotSha256,
    },
    evidence_panel_screenshot: {
      path: panelPath,
      bytes: panelScreenshot.length,
      sha256: panelScreenshotSha256,
    },
    camera_screenshots: cameraScreenshots,
  };
} catch (error) {
  report.error = error instanceof Error ? error.stack || error.message : String(error);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: report.status, report: reportPath, error: report.error || null })}\n`);
}
