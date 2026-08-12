import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

const urlIndex = process.argv.indexOf("--url");
const url = urlIndex >= 0 ? process.argv[urlIndex + 1] : "";
if (!url) throw new Error("--url is required");

const diagnostics = { pageErrors: [], consoleErrors: [], requestFailures: [], httpErrors: [] };
let browser;
try {
  browser = await chromium.launch({ headless: true, args: ["--use-angle=default", "--enable-webgl"] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  page.on("pageerror", error => diagnostics.pageErrors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error") diagnostics.consoleErrors.push(message.text());
  });
  page.on("requestfailed", request => diagnostics.requestFailures.push(`${request.url()} :: ${request.failure()?.errorText || "failed"}`));
  page.on("response", response => {
    if (response.status() >= 400) diagnostics.httpErrors.push(`${response.status()} ${response.url()}`);
  });
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForFunction(() => Boolean(window.spaReview?.ready), null, { timeout: 120000 });
  await page.evaluate(async () => window.spaReview.loadPromise);
  const snapshot = await page.evaluate(() => window.spaReview.snapshot());
  const loaded = Array.isArray(snapshot?.loaded) ? snapshot.loaded.length : snapshot?.assetLoadState?.loaded?.length || 0;
  const failures = Array.isArray(snapshot?.failures) ? snapshot.failures.length : snapshot?.assetLoadState?.failures?.length || 0;
  const passed = snapshot?.status === "loaded" && loaded === 6 && failures === 0
    && Object.values(diagnostics).every(items => items.length === 0);
  process.stdout.write(`${JSON.stringify({ passed, url, loaded, failures, snapshot, diagnostics }, null, 2)}\n`);
  if (!passed) process.exitCode = 1;
} finally {
  if (browser) await browser.close();
}
