import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

const baseUrl = process.argv[2] || "http://127.0.0.1:8768/";
const candidates = process.argv.slice(3);
if (!candidates.length) {
  throw new Error("Pass one or more bounded-text candidate IDs.");
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const pageErrors = [];
const consoleErrors = [];
const activationRequests = [];
page.on("pageerror", error => pageErrors.push(String(error)));
page.on("console", message => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("request", request => {
  if (request.url().endsWith("/api/activate")) {
    activationRequests.push({ method: request.method(), body: request.postDataJSON() });
  }
});

const results = [];
try {
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  for (const candidate of candidates) {
    await page.selectOption("#candidate", candidate);
    const before = await page.locator("#activate").evaluate(button => ({
      disabled: button.disabled,
      text: button.textContent,
    }));
    const activationResponse = page.waitForResponse(response =>
      response.url().endsWith("/api/activate") && response.request().method() === "POST",
    );
    await page.locator("#activate").click();
    await activationResponse;
    await page.waitForFunction(
      () => {
        const stop = document.querySelector("#deactivate");
        const status = document.querySelector("#status")?.textContent || "";
        return stop && !stop.disabled && stop.textContent === "Stop Conversation" && status.includes("Active:");
      },
      undefined,
      { timeout: 10000 },
    );
    const state = await page.evaluate(async () => (await fetch("/api/state")).json());
    results.push({
      candidate,
      before,
      activeCandidate: state.active_candidate,
      activeMode: state.active_conversation_mode,
      statusText: await page.locator("#status").textContent(),
      eventLog: await page.locator("#log").textContent(),
    });
    if (state.active_candidate) {
      const deactivateResponse = page.waitForResponse(response =>
        response.url().endsWith("/api/deactivate") && response.request().method() === "POST",
      );
      await page.locator("#deactivate").click();
      await deactivateResponse;
      await page.waitForFunction(
        () => !document.querySelector("#deactivate") || document.querySelector("#deactivate").disabled,
        undefined,
        { timeout: 10000 },
      );
    }
  }
} finally {
  await browser.close();
}

const report = { baseUrl, results, activationRequests, pageErrors, consoleErrors };
console.log(JSON.stringify(report, null, 2));
if (
  pageErrors.length ||
  consoleErrors.length ||
  activationRequests.length !== candidates.length ||
  results.some(result =>
    result.before.disabled ||
    result.before.text !== "Activate text chat" ||
    result.activeCandidate !== result.candidate ||
    result.activeMode !== "bounded_text_only"
  )
) {
  process.exitCode = 1;
}
