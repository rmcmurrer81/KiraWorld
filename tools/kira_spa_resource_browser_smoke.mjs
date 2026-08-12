import fs from "node:fs";
import path from "node:path";
import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

function option(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

const homeUrl = option("--home-url");
const spaUrl = option("--spa-url");
const readyFile = option("--ready-file");
const stopFile = option("--stop-file");
const maxSeconds = Math.max(15, Number(option("--max-seconds", "180")) || 180);

if (!homeUrl || !spaUrl || !readyFile || !stopFile) {
  throw new Error("--home-url, --spa-url, --ready-file, and --stop-file are required");
}

function recordPageDiagnostics(page, label, diagnostics) {
  page.on("pageerror", (error) => diagnostics.pageErrors.push(`${label}: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.consoleErrors.push(`${label}: ${message.text()}`);
  });
  page.on("requestfailed", (request) => {
    diagnostics.requestFailures.push(`${label}: ${request.url()} :: ${request.failure()?.errorText || "failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) diagnostics.httpErrors.push(`${label}: ${response.status()} ${response.url()}`);
  });
}

async function frameSample(page, seconds = 3) {
  await page.bringToFront();
  return page.evaluate(async (sampleSeconds) => {
    const canvas = document.querySelector("canvas");
    const start = performance.now();
    let frames = 0;
    await new Promise((resolve) => {
      function tick(now) {
        frames += 1;
        if (now - start >= sampleSeconds * 1000) resolve();
        else requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
    const elapsedSeconds = (performance.now() - start) / 1000;
    return {
      frames,
      elapsed_seconds: Number(elapsedSeconds.toFixed(3)),
      frames_per_second: Number((frames / elapsedSeconds).toFixed(2)),
      canvas: canvas ? { width: canvas.width, height: canvas.height } : null,
      js_heap: performance.memory
        ? {
            used_mb: Number((performance.memory.usedJSHeapSize / 1048576).toFixed(2)),
            total_mb: Number((performance.memory.totalJSHeapSize / 1048576).toFixed(2)),
          }
        : null,
    };
  }, seconds);
}

const diagnostics = {
  pageErrors: [],
  consoleErrors: [],
  requestFailures: [],
  httpErrors: [],
};

let browser;
try {
  browser = await chromium.launch({
    headless: true,
    args: ["--use-angle=default", "--enable-webgl"],
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });

  const homePage = await context.newPage();
  recordPageDiagnostics(homePage, "home", diagnostics);
  await homePage.goto(homeUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  await homePage.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.injectShellState), null, { timeout: 120000 });
  await homePage.evaluate(() => {
    window.kiraHomeWorldDebug.injectShellState({
      active_candidate: "kira",
      active_label: "Kira",
      active_ai: "Kira",
      active_form: "civilian",
      active_action: "idle",
      active_model_url: "/models/temp_ai/kira/avatar.glb",
      active_pose_manifest_url: "",
      location: "home",
    });
  });
  await homePage.waitForFunction(
    () => Boolean(window.kiraHomeWorldDebug?.activeAvatarState?.().rootPresent),
    null,
    { timeout: 120000 },
  );
  const homeState = await homePage.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  const homeFrames = await frameSample(homePage);

  const spaPage = await context.newPage();
  recordPageDiagnostics(spaPage, "spa", diagnostics);
  await spaPage.goto(spaUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  await spaPage.waitForFunction(() => Boolean(window.spaReview?.ready), null, { timeout: 120000 });
  await spaPage.evaluate(async () => {
    await window.spaReview.loadPromise;
  });
  const spaState = await spaPage.evaluate(() => window.spaReview.snapshot());
  const spaFrames = await frameSample(spaPage);

  const result = {
    schema_version: 1,
    status: homeState.rootPresent && (spaState?.status === "loaded" || spaState?.assetLoadState?.status === "loaded") ? "ready" : "failed",
    home: { url: homeUrl, active_avatar: homeState, frame_sample: homeFrames },
    spa: { url: spaUrl, snapshot: spaState, frame_sample: spaFrames },
    diagnostics,
  };
  fs.mkdirSync(path.dirname(readyFile), { recursive: true });
  fs.writeFileSync(readyFile, `${JSON.stringify(result, null, 2)}\n`, "utf8");

  const deadline = Date.now() + maxSeconds * 1000;
  while (!fs.existsSync(stopFile) && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  process.stdout.write(`${JSON.stringify(result)}\n`);
} finally {
  if (browser) await browser.close();
}
