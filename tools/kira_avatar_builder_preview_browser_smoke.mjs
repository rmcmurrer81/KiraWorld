import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?:[A-Za-z]:)/, (m) => m.slice(1))), "..");

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function numberOption(name) {
  const raw = option(name, null);
  if (raw === null) return null;
  const value = Number(raw);
  if (!Number.isFinite(value)) throw new Error(`${name} must be a finite number`);
  return value;
}

function fileRecord(filePath) {
  const bytes = fs.readFileSync(filePath);
  return {
    path: path.relative(ROOT, filePath).replaceAll("\\", "/"),
    bytes: bytes.length,
    sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
  };
}

const url = option("--url", "http://127.0.0.1:8770/");
const outputDir = path.resolve(ROOT, option(
  "--out-dir",
  "Data/avatar_builder_workspace_tests/kira_r6_light_eye_preview_20260721",
));
const requestedFit = {
  forward_offset: numberOption("--eye-forward"),
  vertical_offset: numberOption("--eye-vertical"),
  horizontal_offset: numberOption("--eye-horizontal"),
  common_horizontal_offset: numberOption("--eye-common"),
  diameter_scale: numberOption("--eye-scale"),
};
const hasRequestedFit = Object.values(requestedFit).some((value) => value !== null);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"],
});

let evidence = { status: "failed", url, checks: {}, screenshots: {} };
try {
  const page = await browser.newPage({ viewport: { width: 1800, height: 1100 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.waitForFunction(() => {
    const select = document.querySelector("#candidate");
    return select && [...select.options].some((entry) => entry.value === "kira");
  }, null, { timeout: 30_000 });
  await page.selectOption("#candidate", "kira");
  await page.waitForFunction(() => {
    const status = document.querySelector("#previewStatus")?.textContent || "";
    return status.includes("Loaded exact R6 body with the restored pre-R6 light material");
  }, null, { timeout: 45_000 });
  // The Builder starts with engineering guides enabled.  Turn them off for
  // the neutral visual proof so guide boxes cannot be mistaken for eye parts.
  await page.click("#toggleGuides");
  if (hasRequestedFit) {
    await page.evaluate((fit) => {
      const current = window.__avatarBuilderPreviewDebug?.eyeDiagnostics()?.fit || {};
      const requested = Object.fromEntries(
        Object.entries(fit).filter(([, value]) => value !== null),
      );
      if (!window.__avatarBuilderPreviewDebug?.setKiraEyeFit({ ...current, ...requested })) {
        throw new Error("Kira preview eye component is unavailable for reversible fit review");
      }
    }, requestedFit);
    await page.waitForTimeout(250);
  }

  const bodyPath = path.join(outputDir, "kira_builder_r6_light_full_body.png");
  await page.click("#frameBody");
  await page.waitForTimeout(1000);
  await page.screenshot({ path: bodyPath, fullPage: false });

  const headPath = path.join(outputDir, "kira_builder_r6_light_neutral_face.png");
  await page.click("#frameFace");
  await page.waitForTimeout(1000);
  await page.screenshot({ path: headPath, fullPage: false });

  const state = await page.evaluate(() => ({
    title: document.querySelector("#previewTitle")?.textContent || "",
    status: document.querySelector("#previewStatus")?.textContent || "",
    meta: document.querySelector("#previewMeta")?.textContent || "",
    details: document.querySelector("#details")?.innerText || "",
    selected: document.querySelector("#candidate")?.value || "",
    eyeDiagnostics: window.__avatarBuilderPreviewDebug?.eyeDiagnostics?.() || null,
    canvas: (() => {
      const canvas = document.querySelector("#previewCanvas");
      return canvas ? { width: canvas.width, height: canvas.height } : null;
    })(),
  }));

  const eyeAssetPath = path.join(outputDir, "kira_builder_standalone_eye_asset.png");
  await page.click("#inspectEyes");
  await page.waitForFunction(() => {
    const status = document.querySelector("#previewStatus")?.textContent || "";
    return status.includes("Exact staged warm-brown eye component shown by itself");
  }, null, { timeout: 45_000 });
  await page.waitForTimeout(750);
  await page.screenshot({ path: eyeAssetPath, fullPage: false });
  const eyeAssetState = await page.evaluate(() => ({
    title: document.querySelector("#previewTitle")?.textContent || "",
    status: document.querySelector("#previewStatus")?.textContent || "",
    meta: document.querySelector("#previewMeta")?.textContent || "",
  }));

  // Returning to Face must reload the untouched R6 body, not retain the
  // isolated component as though it had been seated in the head.
  await page.click("#frameFace");
  await page.waitForFunction(() => {
    const status = document.querySelector("#previewStatus")?.textContent || "";
    return status.includes("Loaded exact R6 body with the restored pre-R6 light material");
  }, null, { timeout: 45_000 });
  const returnedBodyState = await page.evaluate(() => ({
    title: document.querySelector("#previewTitle")?.textContent || "",
    status: document.querySelector("#previewStatus")?.textContent || "",
    meta: document.querySelector("#previewMeta")?.textContent || "",
  }));

  evidence = {
    status: "passed",
    url,
    state,
    checks: {
      selected_kira: state.selected === "kira",
      exact_r6_loaded: state.meta.includes("kira_provisional_body_r6.glb"),
      original_light_material_applied: state.meta.includes("pre-R6 live light material (untextured)"),
      unsafe_eye_component_not_composed: !state.meta.includes("separate staged warm-brown eye component v3.2") && !state.eyeDiagnostics?.nodes?.KiraLeftEyePivot,
      eye_visual_fit_not_falsely_approved: state.status.includes("hidden") && state.status.includes("visual fit is UNAPPROVED") && state.details.includes("visual fit is UNAPPROVED"),
      standalone_eye_asset_visible_and_labeled: eyeAssetState.title.includes("Eye Component Review") && eyeAssetState.meta.includes("kira_brown_eye_rig_v3_2.glb") && eyeAssetState.status.includes("NOT seated in R6") && eyeAssetState.status.includes("NOT an approved body+eye fit"),
      standalone_eye_asset_does_not_replace_body: returnedBodyState.meta.includes("kira_provisional_body_r6.glb") && returnedBodyState.status.includes("visual fit is UNAPPROVED"),
      anatomy_not_proven_label: state.status.includes("Complete adult anatomy is NOT PROVEN") && state.details.includes("NOT PROVEN"),
      no_browser_errors: errors.length === 0,
    },
    screenshots: {
      full_body: fileRecord(bodyPath),
      neutral_face: fileRecord(headPath),
      standalone_eye_asset: fileRecord(eyeAssetPath),
    },
    browser_errors: errors,
    eye_asset_state: eyeAssetState,
    returned_body_state: returnedBodyState,
    note: "The exact-hash staged brown-eye asset remains hidden from the R6 composite because its seating is unapproved. The standalone Eyes (asset) view makes the component inspectable without implying that it is integrated into Kira's head.",
  };
  if (!Object.values(evidence.checks).every(Boolean)) evidence.status = "failed";
} finally {
  await browser.close();
}

const evidencePath = path.join(outputDir, "evidence.json");
fs.writeFileSync(evidencePath, JSON.stringify(evidence, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ evidence: fileRecord(evidencePath), ...evidence }, null, 2));
if (evidence.status !== "passed") process.exitCode = 1;
