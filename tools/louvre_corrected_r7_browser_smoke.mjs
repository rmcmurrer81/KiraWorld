import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const url = option("--url", "http://127.0.0.1:5197/?solo=1&bookmark=west_arrival");
const reportPath = option("--report", "Data/codex_reports/20260716_louvre_corrected_r7_browser_smoke_final.json");
const screenshotDir = option("--screenshot-dir", "Data/codex_reports/louvre_corrected_r7_screenshots_final");
const diagnostics = { pageErrors: [], consoleErrors: [], requestFailures: [], httpErrors: [] };
let browser;
let report = { schemaVersion: 1, status: "failed", url, diagnostics };

function fileRecord(filePath, bytes) {
  return {
    path: filePath.replaceAll("\\", "/"),
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
  const context = await browser.newContext({ viewport: { width: 1600, height: 960 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on("pageerror", (error) => diagnostics.pageErrors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") diagnostics.consoleErrors.push(message.text()); });
  page.on("requestfailed", (request) => diagnostics.requestFailures.push(`${request.url()} :: ${request.failure()?.errorText || "failed"}`));
  page.on("response", (response) => { if (response.status() >= 400) diagnostics.httpErrors.push(`${response.status()} ${response.url()}`); });

  await page.goto(url, { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForFunction(() => window.__previewReady === true, null, { timeout: 120000 });
  await page.waitForFunction(() => Number(window.__LOUVRE_R7_DEBUG__?.rendererMetrics()?.frameP95Milliseconds) > 0, null, { timeout: 30000 });

  const state = await page.evaluate(() => {
    const debug = window.__LOUVRE_R7_DEBUG__;
    const evidenceAreas = Object.fromEntries(debug.evidence.areas.map((area) => [area.area_id, area.evidence_sufficient_for_draft]));
    const portalStates = debug.evidence.portals.map((portal) => ({
      id: portal.portal_id,
      state: portal.runtime_state,
      solid: portal.collision_solid,
      opens: portal.opens,
    }));
    return {
      buildId: debug.buildId,
      worldId: debug.worldId,
      locationId: debug.locationId,
      status: debug.contract.status,
      rejection: debug.contract.owner_rejection,
      isolation: {
        zeroPeople: debug.zeroPeople,
        peopleLoaded: debug.peopleLoaded,
        mindsLoaded: debug.mindsLoaded,
        voiceLoaded: debug.voiceLoaded,
        homeWorldLoaded: debug.homeWorldLoaded,
        tardisLoaded: debug.tardisLoaded,
      },
      counts: debug.objectCounts(),
      anchors: debug.contract.spatial_anchors,
      evidenceAreas,
      portalStates,
      lockedProbe: debug.lockedPortalProbe(),
      grounding: debug.groundingProbe(-108, 0),
      moveProbes: {
        paving: debug.evaluateExteriorMove([-108, 1.68, 0], [-100, 1.68, 0]),
        main: debug.evaluateExteriorMove([-19, 1.68, 0], [-17, 1.68, 0]),
        northSmall: debug.evaluateExteriorMove([-8, 1.68, -48], [0, 1.68, -48]),
        sully: debug.evaluateExteriorMove([110, 1.68, 0], [113, 1.68, 0]),
      },
      stair: debug.stairSamples(56),
      renderer: debug.rendererMetrics(),
      diagnostics: debug.diagnostics(),
      ui: {
        title: document.title,
        truthRows: document.querySelectorAll(".truth-row").length,
        bookmarkOptions: document.querySelectorAll("#bookmarkSelect option").length,
        feedbackPresent: Boolean(document.getElementById("feedback")),
        pyramidMetric: document.getElementById("pyramidMetric")?.textContent || "",
        portalMetric: document.getElementById("portalMetric")?.textContent || "",
        status: document.getElementById("status")?.textContent || "",
      },
    };
  });

  fs.mkdirSync(screenshotDir, { recursive: true });
  const screenshots = [];
  const views = [
    ["west_arrival", "01_west_arrival.png"],
    ["pyramid_count", "02_main_plus_three_pyramidions.png"],
    ["sully_axis", "03_sully_axis.png"],
    ["lobby_front_study", "04_hall_napoleon_front_study.png"],
    ["lobby_upper_study", "05_hall_napoleon_upper_study.png"],
    ["locked_wings", "06_locked_wing_portals.png"],
  ];
  for (const [bookmark, filename] of views) {
    await page.evaluate((id) => window.__LOUVRE_R7_DEBUG__.setBookmark(id), bookmark);
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const target = path.join(screenshotDir, filename);
    const bytes = await page.screenshot({ path: target });
    screenshots.push({ bookmark, ...fileRecord(target, bytes) });
  }

  const canvas = await page.evaluate(async () => {
    let frames = 0;
    await new Promise((resolve) => {
      const started = performance.now();
      function tick(now) {
        frames += 1;
        if (now - started >= 600) resolve();
        else requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
    const element = document.getElementById("world");
    const gl = element.getContext("webgl2") || element.getContext("webgl");
    const pixels = new Uint8Array(element.width * element.height * 4);
    gl.readPixels(0, 0, element.width, element.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    const colors = new Set();
    const stride = Math.max(1, Math.floor((element.width * element.height) / 2048));
    for (let index = 0; index < element.width * element.height; index += stride) {
      const offset = index * 4;
      colors.add(`${pixels[offset]},${pixels[offset + 1]},${pixels[offset + 2]},${pixels[offset + 3]}`);
    }
    return { width: element.width, height: element.height, frames, uniqueRgbaSamples: colors.size, webgl: gl.getParameter(gl.VERSION) };
  });

  const resources = await page.evaluate(() => performance.getEntriesByType("resource").map((entry) => entry.name));
  assert(state.buildId === "notebook_world_louvre_corrected_r7_20260716_235000", "Unexpected R7 build identity");
  assert(state.status === "corrected_spatial_blockout_not_realism_not_approved", "R7 lost its unapproved-blockout label");
  assert(state.rejection.r5_r6_wide_scan_rejected && !state.rejection.r7_imports_r5_r6_scan_assets, "Rejected scan routing failed");
  assert(state.isolation.zeroPeople && state.isolation.peopleLoaded === 0 && state.isolation.mindsLoaded === 0, "R7 loaded a person or mind");
  assert(!state.isolation.voiceLoaded && !state.isolation.homeWorldLoaded && !state.isolation.tardisLoaded, "R7 loaded voice, Home World, or TARDIS");
  assert(state.counts.mainPyramid === 1 && state.counts.smallerPyramidion === 3, "Pyramid counts are not 1 + 3");
  assert(state.counts.palaceWingGroup === 3 && state.counts.studyStairTread === 56, "Palace/stair topology count drifted");
  assert(state.counts.lockedPortal === 4, "Exactly four physical destination portals must be locked");
  assert(state.counts.person === 0 && state.counts.mind === 0 && state.counts.voice === 0 && state.counts.artwork === 0, "Unsupported runtime objects entered R7");
  assert(state.anchors.main_pyramid.base_width_m === 35 && state.anchors.main_pyramid.height_m === 21, "Official main Pyramid dimensions drifted");
  assert(state.anchors.smaller_pyramidions.count === 3, "Three smaller pyramidions are not contracted");
  assert(JSON.stringify(Object.keys(state.anchors.smaller_pyramidions.centers_m).sort()) === JSON.stringify(["east", "north", "south"]), "Small-pyramid placement keys drifted");
  assert(state.evidenceAreas.cour_napoleon_bounded_exterior && state.evidenceAreas.under_pyramid_hall_napoleon_stair_study, "Exterior or Hall Napoleon bounded-draft gate failed");
  for (const area of ["richelieu_gallery_cells", "sully_gallery_cells", "denon_gallery_cells"]) assert(!state.evidenceAreas[area], `${area} unexpectedly passed evidence`);
  assert(state.portalStates.length === 4 && state.portalStates.every((item) => item.state === "closed_locked_solid" && item.solid && !item.opens), "A physical destination portal is not fail-closed");
  assert(state.lockedProbe.runtimeState === "closed_locked_solid" && state.lockedProbe.collisionSolid && !state.lockedProbe.opens, "Runtime portal probe is not fail-closed");
  assert(state.grounding.surfaceY === 0 && state.grounding.feetDelta === 0, "Exterior grounding drifted");
  assert(state.moveProbes.paving.accepted, "Ordinary exterior paving rejected movement");
  assert(!state.moveProbes.main.accepted && !state.moveProbes.northSmall.accepted && !state.moveProbes.sully.accepted, "A pyramid or palace boundary accepted movement");
  assert(state.stair.length === 57 && state.stair[0].floorY === 0 && state.stair.at(-1).floorY === 6.4, "Visual-study stair endpoints drifted");
  assert(state.stair.every((item, index, all) => item.visualStudyOnly && (index === 0 || item.floorY >= all[index - 1].floorY)), "Visual-study stair samples are invalid");
  assert(state.ui.truthRows === 4 && state.ui.bookmarkOptions === 7 && state.ui.feedbackPresent, "Owner-review UI is incomplete");
  assert(state.ui.pyramidMetric === "1 main + 3 smaller" && state.ui.portalMetric.includes("locked"), "Truth metrics are inaccurate");
  assert(state.renderer.frameP95Milliseconds <= 55, "R7 frame p95 exceeded 55 ms");
  assert(canvas.width > 0 && canvas.height > 0 && canvas.frames > 0 && canvas.uniqueRgbaSamples > 12, "R7 canvas did not visibly render");
  assert(!resources.some((name) => /\.(glb|gltf|fbx)(\?|$)/i.test(name)), "R7 loaded a scan/model resource");
  assert(screenshots.length === 6 && screenshots.every((item) => item.bytes > 10000), "R7 screenshot evidence is missing or empty");
  assert(diagnostics.pageErrors.length === 0, `Page errors: ${diagnostics.pageErrors.join(" | ")}`);
  assert(diagnostics.consoleErrors.length === 0, `Console errors: ${diagnostics.consoleErrors.join(" | ")}`);
  assert(diagnostics.requestFailures.length === 0, `Request failures: ${diagnostics.requestFailures.join(" | ")}`);
  assert(diagnostics.httpErrors.length === 0, `HTTP errors: ${diagnostics.httpErrors.join(" | ")}`);

  report = { ...report, status: "passed", state, canvas, resources, screenshots };
} catch (error) {
  report.error = error instanceof Error ? error.stack || error.message : String(error);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: report.status, report: reportPath, error: report.error || null })}\n`);
}
