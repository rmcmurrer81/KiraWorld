import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const url = process.argv[2] || "http://127.0.0.1:8765/Avatar/runtime3d/dist/index.html?candidate=ladybug_marinette_expanded_smoke&name=Marinette%20%2F%20Ladybug";
const testUrl = `${url}${url.includes("?") ? "&" : "?"}manual=1`;
const output = path.resolve("../../Data/avatar_runtime_tests");
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });

async function verify(name, viewport) {
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(testUrl, { waitUntil: "networkidle" });
  try {
    await page.waitForFunction(() => window.__avatarRuntime?.renderedTriangles > 100, null, { timeout: 15000 });
  } catch (error) {
    const state = await page.evaluate(() => ({
      runtime: window.__avatarRuntime || null,
      body: document.body?.innerText?.slice(0, 500) || "",
    }));
    throw new Error(`${name} did not become render-ready: ${error.message}; browser=${errors.join(" | ")}; state=${JSON.stringify(state)}`);
  }
  await page.locator('[data-action="walk"]').click();
  await page.waitForTimeout(700);
  const walk = await page.evaluate(() => ({ action: window.__avatarRuntime.action, triangles: window.__avatarRuntime.renderedTriangles }));
  await page.locator('[data-action="read_book"]').click();
  await page.waitForTimeout(700);
  const read = await page.evaluate(() => ({ action: window.__avatarRuntime.action, triangles: window.__avatarRuntime.renderedTriangles }));
  const canvas = page.locator("#stage");
  const canvasShot = await canvas.screenshot();
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
    context.drawImage(source, 0, 0, sample.width, sample.height);
    const data = context.getImageData(0, 0, sample.width, sample.height).data;
    const colors = new Set();
    let visible = 0;
    for (let index = 0; index < data.length; index += 16) {
      const alpha = data[index + 3];
      if (alpha > 0) visible += 1;
      colors.add(`${data[index] >> 4},${data[index + 1] >> 4},${data[index + 2] >> 4},${alpha >> 4}`);
    }
    return { visible, distinctColors: colors.size };
  }, canvasDataUrl);
  const box = await canvas.boundingBox();
  await page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true });
  if (errors.length) throw new Error(`${name} browser errors: ${errors.join(" | ")}`);
  if (!box || box.width < viewport.width * 0.95 || box.height < viewport.height * 0.90) throw new Error(`${name} canvas is not full bleed: ${JSON.stringify(box)}`);
  if (walk.action !== "walk" || read.action !== "read_book" || Math.min(walk.triangles, read.triangles) < 100) throw new Error(`${name} runtime actions did not render: ${JSON.stringify({walk,read})}`);
  if (pixels.visible < 200 || pixels.distinctColors < 8) throw new Error(`${name} canvas pixel sample is blank or flat: ${JSON.stringify(pixels)}`);
  return { name, viewport, box, walk, read, pixels };
}

const result = [
  await verify("desktop_1440x900", { width: 1440, height: 900 }),
  await verify("mobile_390x844", { width: 390, height: 844 }),
];
await browser.close();
console.log(JSON.stringify(result, null, 2));
