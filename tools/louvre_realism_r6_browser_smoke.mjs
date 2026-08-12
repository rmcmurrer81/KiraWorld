import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

function option(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const url = option("--url", "http://127.0.0.1:5196/?solo=1&bookmark=arrival");
const reportPath = option("--report", "Data/codex_reports/20260716_louvre_entrance_realism_r6_browser_smoke.json");
const screenshotDir = option("--screenshot-dir", "Data/codex_reports/louvre_entrance_realism_r6_screenshots");
const diagnostics = { pageErrors: [], consoleErrors: [], requestFailures: [], httpErrors: [] };
let browser;
let report = { schemaVersion: 1, status: "failed", url, diagnostics };

function fileRecord(filePath, bytes) {
  return {
    path: filePath,
    bytes: bytes.length,
    sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
  };
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
  page.on("pageerror", (error) => diagnostics.pageErrors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") diagnostics.consoleErrors.push(message.text()); });
  page.on("requestfailed", (request) => diagnostics.requestFailures.push(`${request.url()} :: ${request.failure()?.errorText || "failed"}`));
  page.on("response", (response) => { if (response.status() >= 400) diagnostics.httpErrors.push(`${response.status()} ${response.url()}`); });

  await page.goto(url, { waitUntil: "networkidle", timeout: 180000 });
  await page.waitForFunction(() => window.__previewReady === true, null, { timeout: 180000 });
  await page.waitForFunction(() => Number(window.__LOUVRE_R6_DIAGNOSTICS__?.render?.frameP95Milliseconds) > 0, null, { timeout: 30000 });

  const state = await page.evaluate(async () => {
    const debug = window.__LOUVRE_R6_DEBUG__;
    debug.setAutoStreaming(false);
    await debug.waitForStreamingIdle();
    await debug.setBookmark("arrival");
    const initial = debug.streamingSnapshot();
    const arrivalGrounding = debug.groundingProbe(0, 50, 0);

    const approach = await debug.requestStreamingAt(0, 1.68, 19.2);
    const closedThreshold = debug.thresholdProbe();
    const sideGlassProbe = debug.evaluateMove([8, 1.68, 18.2], [8, 1.68, 17.2]);
    const openingRequested = await debug.setEntranceOpen(true);
    await debug.waitForDoorPhase("open", 8000);
    const openDoor = debug.doorSnapshot();
    const openThreshold = debug.thresholdProbe();
    const down = debug.walkApproximateSpiral("down", 40);
    const up = debug.walkApproximateSpiral("up", 40);
    const guardedOpening = debug.surfaceAt(0, 8, 0);
    const lowerWall = debug.surfaceAt(19, 0, -8);
    const objects = debug.runtimeObjectCounts();
    const resident = debug.streamingSnapshot();
    const metrics = debug.rendererMetrics();

    const far = await debug.requestStreamingAt(0, 1.68, 84);
    const reload = await debug.requestStreamingAt(0, 1.68, 19.2);
    const restoredBeforeDestination = debug.doorSnapshot();
    const restoreOpeningRequested = await debug.setEntranceOpen(true);
    await debug.waitForDoorPhase("open", 8000);
    const restoredAfterDestination = debug.doorSnapshot();
    const restored = debug.streamingSnapshot();

    return {
      buildId: debug.buildId,
      worldId: debug.worldId,
      locationId: debug.locationId,
      isolation: {
        zeroPeople: debug.zeroPeople,
        peopleLoaded: debug.peopleLoaded,
        mindsLoaded: debug.mindsLoaded,
        voiceLoaded: debug.voiceLoaded,
        homeWorldLoaded: debug.homeWorldLoaded,
        tardisLoaded: debug.tardisLoaded,
      },
      initial,
      arrivalGrounding,
      approach,
      collision: { closedThreshold, sideGlassProbe, openThreshold, guardedOpening, lowerWall },
      operation: {
        openingRequested,
        openDoor,
        down,
        up,
        objects,
        resident,
        metrics,
        far,
        reload,
        restoredBeforeDestination,
        restoreOpeningRequested,
        restoredAfterDestination,
        restored,
      },
      diagnostics: debug.diagnostics(),
      ui: {
        title: document.title,
        loadStatus: document.getElementById("loadStatus")?.textContent || "",
        truthRows: document.querySelectorAll(".truth-row").length,
        bookmarkOptions: document.querySelectorAll("#bookmarkSelect option").length,
        doorButton: document.getElementById("doorAction")?.textContent || "",
        feedbackPresent: Boolean(document.getElementById("feedback")),
      },
    };
  });

  const screenshotDefinitions = [
    ["arrival", "01_arrival_real_model_exterior.png"],
    ["entrance", "02_operable_entrance_open.png"],
    ["upper_stair", "03_upper_stair_circulation.png"],
    ["lower_lobby", "04_lower_lobby_locked_boundary.png"],
  ];
  fs.mkdirSync(screenshotDir, { recursive: true });
  const screenshots = [];
  for (const [bookmark, filename] of screenshotDefinitions) {
    await page.evaluate((id) => window.__LOUVRE_R6_DEBUG__.setBookmark(id), bookmark);
    if (bookmark !== "arrival") {
      await page.evaluate(async () => {
        await window.__LOUVRE_R6_DEBUG__.setEntranceOpen(true);
        await window.__LOUVRE_R6_DEBUG__.waitForDoorPhase("open", 8000);
      });
    }
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const target = path.join(screenshotDir, filename);
    const bytes = await page.screenshot({ path: target });
    screenshots.push({ bookmark, ...fileRecord(target, bytes) });
  }

  const canvasSample = await page.evaluate(async () => {
    const canvas = document.getElementById("world");
    let frames = 0;
    await new Promise((resolve) => {
      const started = performance.now();
      function sample(now) {
        frames += 1;
        if (now - started >= 650) resolve();
        else requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
    });
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    const colors = new Set();
    let opaque = 0;
    if (gl && canvas.width > 0 && canvas.height > 0) {
      const pixels = new Uint8Array(canvas.width * canvas.height * 4);
      gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      const stride = Math.max(1, Math.floor((canvas.width * canvas.height) / 2048));
      for (let pixel = 0; pixel < canvas.width * canvas.height; pixel += stride) {
        const offset = pixel * 4;
        colors.add(`${pixels[offset]},${pixels[offset + 1]},${pixels[offset + 2]},${pixels[offset + 3]}`);
        if (pixels[offset + 3] > 0) opaque += 1;
      }
    }
    return {
      width: canvas.width,
      height: canvas.height,
      frames,
      uniqueRgbaSamples: colors.size,
      opaqueSamples: opaque,
      webglVersion: gl?.getParameter(gl.VERSION) || null,
      webglVendor: gl?.getParameter(gl.VENDOR) || null,
      webglRenderer: gl?.getParameter(gl.RENDERER) || null,
    };
  });

  const resourceEntries = await page.evaluate(() => performance.getEntriesByType("resource")
    .filter((entry) => entry.name.endsWith(".glb"))
    .map((entry) => ({
      filename: entry.name.split("/").at(-1),
      durationMilliseconds: Number(entry.duration.toFixed(1)),
      transferSize: entry.transferSize,
      encodedBodySize: entry.encodedBodySize,
      decodedBodySize: entry.decodedBodySize,
    })));

  const cells = ["cour_napoleon_real_model_exterior", "pyramid_entrance_transition", "under_pyramid_lower_lobby_stair"];
  assert(state.isolation.zeroPeople && state.isolation.peopleLoaded === 0 && state.isolation.mindsLoaded === 0, "R6 loaded a person or mind");
  assert(!state.isolation.voiceLoaded && !state.isolation.homeWorldLoaded && !state.isolation.tardisLoaded, "R6 loaded voice, Home World, or TARDIS state");
  assert(state.initial.contract_status === "streaming_scaffold_only_not_complete", "R6 lost the explicit incomplete status");
  assert(JSON.stringify(state.initial.managed_loaded_cells) === JSON.stringify([cells[0]]), "Arrival must contain only the real-model exterior cell");
  assert(state.arrivalGrounding.resolved_surface_y_m === 0 && state.arrivalGrounding.feet_delta_m === 0, "Arrival eye/feet grounding drifted");
  assert(JSON.stringify(state.approach.managed_loaded_cells) === JSON.stringify(cells.slice(0, 2)), "Distance alone loaded the portal-gated lower cell");
  assert(state.collision.closedThreshold.accepted === false && state.collision.closedThreshold.door.thresholdCollisionSolid, "Closed entrance did not fail closed");
  assert(state.collision.sideGlassProbe.accepted === false, "A non-door Pyramid glass crossing was accepted");
  assert(state.operation.openingRequested && state.operation.openDoor.phase === "open", "Door did not reach open after destination staging");
  assert(state.operation.openDoor.destinationReady && state.operation.openDoor.thresholdPassable, "Door opened before destination collision became ready");
  assert(state.collision.openThreshold.accepted === true, "Open validated threshold rejected crossing");
  assert(state.operation.down.length === 41 && state.operation.up.length === 41, "Spiral smoke did not sample 40 intervals and both endpoints");
  assert(state.operation.down.every((sample) => sample.accepted), "Spiral descent contains an ungrounded sample");
  assert(state.operation.up.every((sample) => sample.accepted), "Spiral return contains an ungrounded sample");
  assert(state.operation.down[0].floor_y_m === 0 && state.operation.down.at(-1).floor_y_m === -8, "Spiral descent endpoints drifted");
  assert(state.operation.down.every((sample, index, all) => index === 0 || sample.floor_y_m <= all[index - 1].floor_y_m), "Spiral descent is not monotonic");
  assert(state.operation.up.every((sample, index, all) => index === 0 || sample.floor_y_m >= all[index - 1].floor_y_m), "Spiral return is not monotonic");
  assert(state.collision.guardedOpening === null && state.collision.lowerWall === null, "Guarded opening or bounded lower wall exposed an unsupported walk surface");
  assert(state.operation.objects.doorLeaf === 2 && state.operation.objects.stairTread === 40, "Door or stair topology count drifted");
  for (const unsupported of ["person", "mind", "voice", "elevator", "escalator", "gallery", "artwork"]) {
    assert(state.operation.objects[unsupported] === 0, `Unsupported ${unsupported} object entered R6`);
  }
  assert(JSON.stringify(state.operation.resident.managed_loaded_cells) === JSON.stringify(cells), "Validated transition did not keep all three bounded cells resident");
  assert(JSON.stringify(state.operation.far.managed_loaded_cells) === JSON.stringify([cells[0]]), "Far return did not unload both bounded transition cells");
  assert(state.operation.far.persistent_state_cells.includes(cells[1]) && state.operation.far.persistent_state_cells.includes(cells[2]), "Unload did not capture entrance and stair state");
  assert(state.operation.far.portal_authorized_cells.length === 0, "Lower-cell portal authorization did not expire on unload");
  assert(JSON.stringify(state.operation.reload.managed_loaded_cells) === JSON.stringify(cells.slice(0, 2)), "Reload approach bypassed the lower-cell portal gate");
  assert(state.operation.restoredBeforeDestination.progress === 1 && !state.operation.restoredBeforeDestination.thresholdPassable, "Restored open leaf state became passable without its destination");
  assert(state.operation.restoreOpeningRequested && state.operation.restoredAfterDestination.thresholdPassable, "Restored entrance did not become passable after revalidation");
  assert(JSON.stringify(state.operation.restored.managed_loaded_cells) === JSON.stringify(cells), "Restored bounded cell set is incomplete");
  const budget = state.operation.resident.resource_budgets.active_set;
  assert(state.operation.metrics.triangles <= budget.max_triangles, "Measured renderer triangles exceeded the R6 ceiling");
  assert(state.operation.metrics.draw_calls <= budget.max_draw_calls, "Measured draw calls exceeded the R6 ceiling");
  assert(state.diagnostics.render.frameP95Milliseconds <= 55, "R6 frame p95 exceeded the private review ceiling");
  assert(state.ui.truthRows === 4 && state.ui.bookmarkOptions === 4 && state.ui.feedbackPresent, "R6 truth, bookmark, or feedback UI is incomplete");
  assert(state.ui.loadStatus.startsWith("Supplied real-model exterior ready"), "R6 did not expose its ready status accurately");
  assert(canvasSample.width > 0 && canvasSample.height > 0 && canvasSample.frames > 0, "R6 canvas did not render");
  assert(canvasSample.uniqueRgbaSamples > 8 && canvasSample.opaqueSamples > 0, "R6 canvas lacks visible variation");
  assert(screenshots.length === 4 && screenshots.every((item) => item.bytes > 10_000), "R6 screenshot evidence is incomplete or empty");
  const loadedAssetNames = new Set(resourceEntries.filter((entry) => entry.decodedBodySize > 0 || entry.transferSize > 0).map((entry) => entry.filename));
  const benignAborts = diagnostics.requestFailures.filter((failure) => [...loadedAssetNames].some((name) => failure.includes(name) && failure.includes("ERR_ABORTED")));
  const unexpectedFailures = diagnostics.requestFailures.filter((failure) => !benignAborts.includes(failure));
  assert(diagnostics.pageErrors.length === 0, `Page errors: ${diagnostics.pageErrors.join(" | ")}`);
  assert(diagnostics.consoleErrors.length === 0, `Console errors: ${diagnostics.consoleErrors.join(" | ")}`);
  assert(unexpectedFailures.length === 0, `Request failures: ${unexpectedFailures.join(" | ")}`);
  assert(diagnostics.httpErrors.length === 0, `HTTP errors: ${diagnostics.httpErrors.join(" | ")}`);

  report = {
    ...report,
    status: "passed",
    state,
    canvas: canvasSample,
    resources: resourceEntries,
    screenshots,
    benignLoadedGlbAborts: benignAborts,
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
