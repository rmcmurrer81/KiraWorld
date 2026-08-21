import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const candidate = process.argv[2] || "ladybug_marinette_expanded_smoke";
const display = process.argv[3] || "Marinette / Ladybug";
const url = `http://127.0.0.1:8765/Avatar/runtime3d/dist/index.html?candidate=${encodeURIComponent(candidate)}&name=${encodeURIComponent(display)}`;
const statePath = path.resolve(`../state/temp_ai/${candidate}.json`);
const original = await fs.readFile(statePath, "utf8");
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 500, height: 760 } });

async function writeState(action, activity) {
  const state = JSON.parse(original);
  state.updated_at = new Date().toISOString();
  state.action = action;
  state.activity = activity;
  await fs.writeFile(statePath, JSON.stringify(state, null, 2));
}

async function sample() {
  return page.evaluate(() => ({
    action: window.__avatarRuntime?.action,
    modelMode: window.__avatarRuntime?.modelMode,
    triangles: window.__avatarRuntime?.renderedTriangles,
    status: document.querySelector("#status")?.textContent,
  }));
}

try {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__avatarRuntime?.renderedTriangles > 100);
  await writeState("use_computer", "working during a supervised life-loop cycle");
  await page.waitForFunction(() => window.__avatarRuntime?.action === "use_computer", null, { timeout: 7000 });
  const working = await sample();
  await writeState("talking", "talking with Robert while the life loop continues");
  await page.waitForFunction(() => window.__avatarRuntime?.action === "talking", null, { timeout: 7000 });
  const talking = await sample();
  if (working.triangles < 100 || talking.triangles < 100) {
    throw new Error(`Avatar became blank during state changes: ${JSON.stringify({ working, talking })}`);
  }
  if (working.modelMode !== talking.modelMode) {
    throw new Error(`Appearance mode changed unexpectedly: ${JSON.stringify({ working, talking })}`);
  }
  console.log(JSON.stringify({ candidate, working, talking }, null, 2));
} finally {
  await fs.writeFile(statePath, original);
  await browser.close();
}
