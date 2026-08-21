import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const baseUrl = process.argv[2] || "http://127.0.0.1:8765";
const url = `${baseUrl}/Avatar/runtime3d/dist/index.html?candidate=ladybug_marinette_expanded_smoke&name=${encodeURIComponent("Marinette / Ladybug")}&manual=1`;
const here = path.dirname(fileURLToPath(import.meta.url));
const output = path.resolve(here, "../../Data/avatar_runtime_tests/ladybug_model_v1");
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });

async function verify(name, viewport) {
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on("console", message => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(
    () => window.__avatarRuntime?.modelMode === "rigged" && window.__avatarRuntime?.renderedTriangles > 500,
    null,
    { timeout: 15000 },
  );

  const motionBefore = await page.evaluate(() => window.__avatarRuntime.motionSample);
  await page.waitForTimeout(900);
  const motionAfter = await page.evaluate(() => window.__avatarRuntime.motionSample);
  if (!motionBefore || !motionAfter || motionBefore.every((value, index) => Math.abs(value - motionAfter[index]) < 0.0001)) {
    throw new Error(`${name} model loaded but showed no idle movement`);
  }

  async function inspectCanvas(label) {
    await page.evaluate(() => new Promise(resolve => {
      let frames = 0;
      const waitFrame = () => {
        frames += 1;
        if (frames >= 6) resolve();
        else requestAnimationFrame(waitFrame);
      };
      requestAnimationFrame(waitFrame);
    }));
    await page.waitForTimeout(650);
    const canvasShot = await page.locator("#stage").screenshot();
    const canvasDataUrl = `data:image/png;base64,${canvasShot.toString("base64")}`;
    const pixels = await page.evaluate(async dataUrl => {
      const source = new Image();
      await new Promise((resolve, reject) => {
        source.onload = resolve;
        source.onerror = reject;
        source.src = dataUrl;
      });
      const sample = document.createElement("canvas");
      sample.width = 64;
      sample.height = 64;
      const context = sample.getContext("2d", { willReadFrequently: true });
      context.drawImage(source, 0, 0, 64, 64);
      const data = context.getImageData(0, 0, 64, 64).data;
      const colors = new Set();
      let nonBackground = 0;
      for (let index = 0; index < data.length; index += 16) {
        const key = `${data[index] >> 4},${data[index + 1] >> 4},${data[index + 2] >> 4}`;
        colors.add(key);
        if (data[index] > 45 || data[index + 1] > 45 || data[index + 2] > 45) nonBackground += 1;
      }
      return { distinctColors: colors.size, nonBackground };
    }, canvasDataUrl);
    if (pixels.distinctColors < 10 || pixels.nonBackground < 200) {
      throw new Error(`${name} ${label} canvas appears blank: ${JSON.stringify(pixels)}`);
    }
    return pixels;
  }

  await page.locator('[data-form="hero"]').click();
  const hero = await page.evaluate(() => ({
    form: window.__avatarRuntime.form,
    mode: window.__avatarRuntime.modelMode,
    triangles: window.__avatarRuntime.renderedTriangles,
    status: document.querySelector("#status")?.textContent,
  }));
  hero.pixels = await inspectCanvas("hero");
  await page.screenshot({ path: path.join(output, `${name}_hero.png`), fullPage: true });

  await page.locator('[data-form="civilian"]').click();
  const civilian = await page.evaluate(() => ({
    form: window.__avatarRuntime.form,
    mode: window.__avatarRuntime.modelMode,
    triangles: window.__avatarRuntime.renderedTriangles,
    status: document.querySelector("#status")?.textContent,
  }));
  civilian.pixels = await inspectCanvas("civilian");
  await page.screenshot({ path: path.join(output, `${name}_civilian.png`), fullPage: true });

  if (errors.length) throw new Error(`${name} browser errors: ${errors.join(" | ")}`);
  if (hero.mode !== "rigged" || civilian.mode !== "rigged") throw new Error(`${name} did not keep the GLB loaded`);
  if (hero.form !== "hero" || civilian.form !== "civilian") throw new Error(`${name} form controls failed`);
  if (Math.min(hero.triangles, civilian.triangles) < 500) throw new Error(`${name} rendered too few triangles`);
  await page.close();
  return { name, viewport, motionBefore, motionAfter, hero, civilian };
}

try {
  const results = [
    await verify("desktop_1440x900", { width: 1440, height: 900 }),
    await verify("mobile_390x844", { width: 390, height: 844 }),
  ];
  console.log(JSON.stringify(results, null, 2));
} finally {
  await browser.close();
}
