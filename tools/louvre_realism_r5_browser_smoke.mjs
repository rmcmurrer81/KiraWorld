import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

function option(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

function required(name) {
  const value = option(name);
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const url = required("--url");
const reportPath = required("--report");
const screenshotDir = required("--screenshot-dir");
const diagnostics = { pageErrors: [], consoleErrors: [], requestFailures: [], httpErrors: [] };
let browser;
let report = { schemaVersion: 1, status: "failed", url, diagnostics };

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
  await page.waitForFunction(() => window.__LOUVRE_R5_DIAGNOSTICS__?.contextCell?.state === "loaded" && window.__LOUVRE_R5_DIAGNOSTICS__?.facadeCell?.state === "loaded", null, { timeout: 180000 });
  await page.waitForFunction(() => Number(window.__LOUVRE_R5_DIAGNOSTICS__?.render?.frameP95Milliseconds) > 0, null, { timeout: 30000 });
  await page.waitForTimeout(1500);

  const state = await page.evaluate(async () => {
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const canvas = document.querySelector("#world");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    const debugInfo = gl?.getExtension("WEBGL_debug_renderer_info");
    const resources = performance.getEntriesByType("resource").filter((entry) => entry.name.includes("the_louvre_context_cutout96m_source_mesh.glb") || entry.name.includes("pavillon_sully_facade_lod600k.glb"));
    return {
      diagnostics: JSON.parse(JSON.stringify(window.__LOUVRE_R5_DIAGNOSTICS__)),
      ui: {
        title: document.title,
        loadStatus: document.querySelector("#loadStatus")?.textContent || "",
        truthRows: document.querySelectorAll(".truth-row").length,
        bookmarkOptions: document.querySelectorAll("#bookmarkSelect option").length,
        feedbackPresent: Boolean(document.querySelector("#feedback")),
      },
      canvas: { width: canvas.width, height: canvas.height },
      webgl: {
        version: gl?.getParameter(gl.VERSION) || null,
        vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl?.getParameter(gl.VENDOR) || null,
        renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl?.getParameter(gl.RENDERER) || null,
        maxTextureSize: gl?.getParameter(gl.MAX_TEXTURE_SIZE) || null,
      },
      resources: resources.map((resource) => ({
        filename: resource.name.split("/").at(-1),
        durationMilliseconds: Number(resource.duration.toFixed(2)),
        transferSize: resource.transferSize,
        encodedBodySize: resource.encodedBodySize,
        decodedBodySize: resource.decodedBodySize,
      })),
    };
  });
  const benignLoadedGlbAborts = diagnostics.requestFailures.filter((item) =>
    item.includes("net::ERR_ABORTED")
    && (item.includes("the_louvre_context_cutout96m_source_mesh.glb") || item.includes("pavillon_sully_facade_lod600k.glb")),
  );
  const fatalRequestFailures = diagnostics.requestFailures.filter((item) => !benignLoadedGlbAborts.includes(item));

  fs.mkdirSync(screenshotDir, { recursive: true });
  const screenshots = [];
  const bookmarks = ["arrival", "pyramid_close", "west_context", "east_context", "rear_context"];
  for (const [index, bookmark] of bookmarks.entries()) {
    await page.locator("#bookmarkSelect").selectOption(bookmark);
    await page.waitForTimeout(250);
    const filename = `${String(index + 1).padStart(2, "0")}_${bookmark}.png`;
    const filePath = path.join(screenshotDir, filename);
    const bytes = await page.screenshot({ path: filePath });
    screenshots.push({
      bookmark,
      path: filePath,
      bytes: bytes.length,
      sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
    });
  }

  assert(state.diagnostics.reviewStatus === "owner_review_ready", "R5 did not reach owner-review readiness");
  assert(state.diagnostics.contextCell.state === "loaded", "Real-model context cell is not loaded");
  assert(state.diagnostics.facadeCell.state === "loaded", "Pavillon Sully facade cell is not loaded");
  assert(state.diagnostics.isolation.activePeople === 0, "A person entered the solo review");
  assert(state.diagnostics.isolation.personSystemsLoaded === false, "Person systems were loaded");
  assert(state.diagnostics.isolation.mindSystemsLoaded === false && state.diagnostics.isolation.voiceSystemsLoaded === false, "Mind or voice systems were loaded");
  assert(state.diagnostics.truth.suppliedRealModelContext === true, "Supplied context truth flag is missing");
  assert(state.diagnostics.truth.exactDigitalTwin === false && state.diagnostics.truth.exactScan === false, "R5 overclaims exactness");
  assert(state.diagnostics.truth.fullInterior === false, "R5 overclaims a full interior");
  assert(state.diagnostics.truth.workingDoor === false && state.diagnostics.truth.workingStairs === false, "R5 overclaims door/stair mechanics");
  assert(state.diagnostics.truth.workingElevator === false && state.diagnostics.truth.workingEscalator === false, "R5 overclaims vertical transport");
  assert(state.diagnostics.truth.galleryInventory === false && state.diagnostics.truth.artworkInventory === false, "R5 overclaims gallery/artwork content");
  assert(state.diagnostics.sourceAsset.sha256 === "1a1e69277cbe968e3155d4adf9304a2a51e0be581d949b2184fed2850cb87ecb", "Runtime asset hash drifted");
  assert(state.diagnostics.sourceAsset.triangles === 951_353, "Runtime source-triangle declaration drifted");
  assert(state.diagnostics.facadeAsset.sha256 === "9015233de2e77a24aea77ad342589c8b78eeff0f3c4021cc890ee22af9ef2d68", "Runtime facade hash drifted");
  assert(state.diagnostics.facadeAsset.triangles === 599_959 && state.diagnostics.facadeAsset.sourceLicense === "CC BY-NC-SA 4.0", "Facade geometry/license declaration drifted");
  assert(state.diagnostics.contextCell.boundsMeters.every((value) => Number.isFinite(value) && value > 0), "Context bounds were not measured");
  assert(state.diagnostics.facadeCell.boundsMeters.every((value) => Number.isFinite(value) && value > 0), "Facade bounds were not measured");
  assert(state.diagnostics.render.triangles >= 1_500_000, "Rendered triangle count does not include both real-model context cells");
  assert(state.diagnostics.render.calls > 0 && state.diagnostics.render.calls < 250, "Draw calls are absent or exceed the R5 review ceiling");
  assert(state.diagnostics.render.frameP95Milliseconds > 0 && state.diagnostics.render.frameP95Milliseconds < 55, "Frame p95 exceeds the 55 ms owner-review ceiling");
  assert(state.ui.truthRows === 4 && state.ui.bookmarkOptions === 5 && state.ui.feedbackPresent, "Truth/bookmark/feedback UI is incomplete");
  assert(state.ui.loadStatus.includes("Real-model site and eye-level Pavillon Sully context loaded"), "Loaded truth status is not visible");
  assert(state.canvas.width > 0 && state.canvas.height > 0 && state.webgl.version, "WebGL canvas did not initialize");
  assert(state.resources.some((item) => item.filename === "the_louvre_context_cutout96m_source_mesh.glb" && item.decodedBodySize === 107_547_856), "Wide-context GLB byte evidence is missing");
  assert(state.resources.some((item) => item.filename === "pavillon_sully_facade_lod600k.glb" && item.decodedBodySize === 30_439_072), "Facade GLB byte evidence is missing");
  assert(screenshots.every((item) => item.bytes > 30_000), "One or more review screenshots are unexpectedly small");
  assert(diagnostics.pageErrors.length === 0, `Page errors: ${diagnostics.pageErrors.join(" | ")}`);
  assert(diagnostics.consoleErrors.length === 0, `Console errors: ${diagnostics.consoleErrors.join(" | ")}`);
  assert(fatalRequestFailures.length === 0, `Request failures: ${fatalRequestFailures.join(" | ")}`);
  assert(diagnostics.httpErrors.length === 0, `HTTP errors: ${diagnostics.httpErrors.join(" | ")}`);

  report = { ...report, status: "passed", state, screenshots, benignLoadedGlbAborts };
} catch (error) {
  report.error = error instanceof Error ? error.stack || error.message : String(error);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: report.status, report: reportPath, error: report.error || null })}\n`);
}
