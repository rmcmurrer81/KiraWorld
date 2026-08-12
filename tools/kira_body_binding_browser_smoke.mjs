import crypto from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PREVIEW_ROOT = path.join(
  ROOT,
  "Data", "world_builds", "notebook_worlds", "home_world", "builds",
  "home_world_main_house_20260630_223000", "preview",
);
const PROFILE = path.join(ROOT, "Avatar", "state", "temp_ai", "kira.json");
const SELECTION = path.join(ROOT, "Avatar", "state", "body_selections", "kira_runtime_body_selection.json");
const EXPECTED_MODEL_FRAGMENT = "kira_provisional_body_r6.glb";
const EXPECTED_MODEL_SHA256 = "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77";

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
}

async function waitForHttp(url, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.status < 500) return;
    } catch {
      // Server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function stopChild(child) {
  if (!child || child.killed) return;
  child.kill();
  await new Promise((resolve) => {
    const timer = setTimeout(resolve, 3_000);
    child.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

const before = { profile: sha256(PROFILE), selection: sha256(SELECTION) };
let builder = null;
let vite = null;
let browser = null;
let fatalError = null;
const evidence = {
  generated_at: new Date().toISOString(),
  purpose: "Read-only body-binding and fail-closed renderer smoke test",
  topology_changed: false,
  complete_adult_anatomy_proven: false,
  checks: {},
};

try {
  const builderPort = await freePort();
  const vitePort = await freePort();
  builder = spawn("python", ["tools/avatar_builder_workspace_server.py", "--no-browser"], {
    cwd: ROOT,
    env: { ...process.env, KIRA_AVATAR_BUILDER_PORT: String(builderPort) },
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
  const viteEntry = path.join(PREVIEW_ROOT, "node_modules", "vite", "bin", "vite.js");
  vite = spawn(process.execPath, [viteEntry, "--host", "127.0.0.1", "--port", String(vitePort), "--strictPort"], {
    cwd: PREVIEW_ROOT,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  const builderUrl = `http://127.0.0.1:${builderPort}/?candidate=kira`;
  const worldUrl = `http://127.0.0.1:${vitePort}/?area=home&bodyBindingSmoke=1`;
  await Promise.all([waitForHttp(builderUrl), waitForHttp(worldUrl)]);

  browser = await chromium.launch({ headless: true, args: ["--enable-webgl", "--ignore-gpu-blocklist"] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto(builderUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForFunction(() => document.querySelector("#candidate")?.value === "kira", null, { timeout: 120_000 });
  await page.waitForFunction(() => document.querySelector("#details")?.textContent?.includes("NOT PROVEN"), null, { timeout: 120_000 });
  const builderState = await page.evaluate(async () => {
    const response = await fetch("/api/state", { cache: "no-store" });
    const state = await response.json();
    const kira = (state.candidates || []).find((item) => item.id === "kira");
    return {
      selected: document.querySelector("#candidate")?.value || null,
      details: document.querySelector("#details")?.textContent || "",
      runtime_model_url: kira?.runtime_model_url || "",
      builder_preview_model_url: kira?.builder_preview_model_url || "",
      preview_model_url: kira?.preview_model_url || "",
      runtime_body_selection_valid: kira?.runtime_body_selection_valid === true,
      runtime_body_profile_matches_selection: kira?.runtime_body_profile_matches_selection === true,
      adult_external_form_trial: kira?.adult_external_form_trial === true,
      complete_adult_anatomy_proven: kira?.complete_adult_anatomy_proven === true,
    };
  });
  evidence.builder = builderState;
  evidence.checks.builder_selected_kira = builderState.selected === "kira";
  evidence.checks.builder_runtime_uses_exact_r6 = builderState.runtime_model_url.includes(EXPECTED_MODEL_FRAGMENT);
  evidence.checks.builder_preview_uses_same_r6 = builderState.builder_preview_model_url === builderState.runtime_model_url
    && builderState.preview_model_url === builderState.runtime_model_url;
  evidence.checks.builder_profile_matches_selection = builderState.runtime_body_selection_valid
    && builderState.runtime_body_profile_matches_selection;
  evidence.checks.builder_labels_external_form_trial = builderState.adult_external_form_trial
    && builderState.details.includes("R6 adult external-form owner-review trial");
  evidence.checks.builder_says_complete_anatomy_not_proven = !builderState.complete_adult_anatomy_proven
    && builderState.details.includes("Complete Adult Anatomy")
    && builderState.details.includes("NOT PROVEN");

  await page.goto(worldUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.injectShellState), null, { timeout: 120_000 });
  await page.evaluate(() => window.kiraHomeWorldDebug.injectShellState({
    active_candidate: "kira",
    active_label: "Kira",
    active_ai: "Kira",
    active_form: "fail_closed_browser_smoke",
    active_action: "idle",
    active_model_url: "",
    active_pose_manifest_url: "",
    active_body_selection: {
      enforced: true,
      valid: false,
      reason: "browser_smoke_missing_exact_selected_model",
    },
    location: "home",
    isolated_browser_test: true,
    do_not_persist: true,
  }));
  await page.waitForTimeout(250);
  const noModelState = await page.evaluate(() => window.kiraHomeWorldDebug.activeAvatarState());
  evidence.no_model_renderer = noModelState;
  evidence.checks.no_model_fails_closed = noModelState.markerKind === "body_load_blocked_fail_closed";
  evidence.checks.no_model_has_no_loaded_body = noModelState.rootPresent === false;
  evidence.checks.no_model_has_no_sphere_or_other_child = noModelState.markerChildCount === 0;
} catch (error) {
  fatalError = error?.stack || error?.message || String(error);
} finally {
  if (browser) await browser.close();
  await stopChild(builder);
  await stopChild(vite);
}

const after = { profile: sha256(PROFILE), selection: sha256(SELECTION) };
evidence.profile_sha256_before = before.profile;
evidence.profile_sha256_after = after.profile;
evidence.selection_sha256_before = before.selection;
evidence.selection_sha256_after = after.selection;
evidence.checks.profile_unchanged_by_browser_test = before.profile === after.profile;
evidence.checks.selection_unchanged_by_browser_test = before.selection === after.selection;

const profile = JSON.parse(fs.readFileSync(PROFILE, "utf8"));
const selection = JSON.parse(fs.readFileSync(SELECTION, "utf8"));
evidence.profile_model_url = profile.model_url || "";
evidence.selected_model_sha256 = selection.review_candidate?.sha256 || "";
evidence.checks.profile_remains_exact_r6 = evidence.profile_model_url.includes(EXPECTED_MODEL_FRAGMENT);
evidence.checks.selected_hash_remains_exact_r6 = evidence.selected_model_sha256 === EXPECTED_MODEL_SHA256;
evidence.fatal_error = fatalError;
evidence.status = !fatalError && Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";

const stamp = evidence.generated_at.replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
const reportDir = path.join(ROOT, "Data", "world_tests", "kira_body_binding_browser_smoke_20260719", stamp);
fs.mkdirSync(reportDir, { recursive: true });
const reportPath = path.join(reportDir, "evidence.json");
fs.writeFileSync(reportPath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");

process.stdout.write(`${JSON.stringify({
  status: evidence.status,
  report: path.relative(ROOT, reportPath).replaceAll("\\", "/"),
  checks: evidence.checks,
  fatal_error: fatalError,
}, null, 2)}\n`);
if (evidence.status !== "passed") process.exitCode = 1;
