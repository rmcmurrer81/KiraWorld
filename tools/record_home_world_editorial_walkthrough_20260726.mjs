import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PREVIEW = path.join(
  ROOT, "Data", "world_builds", "notebook_worlds", "home_world", "builds",
  "home_world_main_house_20260630_223000", "preview",
);
const OUTPUT = path.join(ROOT, "Data", "video_studio_editorial_sources", "20260726");
fs.mkdirSync(OUTPUT, { recursive: true });

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

async function waitForHttp(url) {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.status < 500) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error("Home World preview did not start");
}

let vite;
let browser;
try {
  const port = await freePort();
  const viteEntry = path.join(PREVIEW, "node_modules", "vite", "bin", "vite.js");
  vite = spawn(process.execPath, [viteEntry, "--host", "127.0.0.1", "--port", String(port), "--strictPort"], {
    cwd: PREVIEW, windowsHide: true, stdio: ["ignore", "pipe", "pipe"],
  });
  const url = `http://127.0.0.1:${port}/?area=home&kiraEyeRig=v3.3`;
  await waitForHttp(url);
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-angle=swiftshader"],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: OUTPUT, size: { width: 1280, height: 720 } },
  });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug), null, { timeout: 120000 });
  await page.waitForTimeout(10000);
  await page.evaluate(() => {
    window.kiraHomeWorldDebug.injectShellState({
      active_candidate: "kira",
      active_label: "Kira",
      active_ai: "Kira",
      active_action: "idle",
      active_form: "civilian",
      active_model_url: "/models/temp_ai/kira/avatar.glb",
      location: "home",
      isolated_browser_test: true,
      do_not_persist: true,
    });
  });
  await page.waitForTimeout(8000);
  const route = [
      { x: -26.7, y: 1.65, z: 17.6, yaw: 0.0, pitch: -0.05, dwell: 2200 },
      { x: -25.8, y: 1.65, z: 14.0, yaw: 0.0, pitch: 0.0, dwell: 700 },
      { x: -23.85, y: 1.65, z: 10.55, yaw: 0.0, pitch: 0.0, dwell: 1400 },
      { x: -21.2, y: 1.65, z: 7.5, yaw: -0.35, pitch: 0.0, dwell: 900 },
      { x: -19.55, y: 1.65, z: 4.45, yaw: -0.9, pitch: -0.05, dwell: 2200 },
      { x: -18.9, y: 1.65, z: 0.7, yaw: -0.78, pitch: -0.03, dwell: 2200 },
      { x: -22.0, y: 1.65, z: -0.1, yaw: 1.25, pitch: -0.02, dwell: 1000 },
      { x: -25.9, y: 1.65, z: 0.32, yaw: 1.57, pitch: -0.02, dwell: 1900 },
      { x: -27.55, y: 1.65, z: 5.5, yaw: 1.57, pitch: -0.05, dwell: 2400 },
      { x: -23.85, y: 1.65, z: 10.55, yaw: 3.14, pitch: 0.0, dwell: 1200 },
      { x: -26.7, y: 1.65, z: 17.6, yaw: 3.14, pitch: -0.08, dwell: 2600 },
    ];
  await page.evaluate((position) => window.kiraHomeWorldDebug.setPlayerPosition(position), route[0]);
  for (let index = 1; index < route.length; index += 1) {
    const from = route[index - 1];
    const to = route[index];
    const frames = 18;
    for (let frame = 1; frame <= frames; frame += 1) {
      const t = frame / frames;
      await page.evaluate((position) => {
        window.kiraHomeWorldDebug.setPlayerPosition(position);
      }, {
          x: from.x + (to.x - from.x) * t,
          y: from.y + (to.y - from.y) * t,
          z: from.z + (to.z - from.z) * t,
          yaw: from.yaw + (to.yaw - from.yaw) * t,
          pitch: from.pitch + (to.pitch - from.pitch) * t,
          floor: 0,
      });
      await page.waitForTimeout(90);
    }
    await page.waitForTimeout(to.dwell);
  }
  await page.waitForTimeout(3000);
  const video = page.video();
  await context.close();
  const recorded = await video.path();
  const target = path.join(OUTPUT, "HOME_WORLD_CONTINUOUS_WALKTHROUGH.webm");
  fs.copyFileSync(recorded, target);
  const result = {
    status: "RECORDED",
    source: url,
    output: target,
    bytes: fs.statSync(target).size,
    mode: "isolated_browser_capture_no_mind_no_voice_no_persistence",
  };
  fs.writeFileSync(path.join(OUTPUT, "HOME_WORLD_CONTINUOUS_WALKTHROUGH.json"), JSON.stringify(result, null, 2));
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} finally {
  if (browser) await browser.close().catch(() => {});
  if (vite && !vite.killed) vite.kill();
}
