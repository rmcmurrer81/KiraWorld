import crypto from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPORT_ROOT = path.join(ROOT, "Data", "world_tests", "kira_text_voice_profiles_20260718");
const REPORT_PATH = path.join(REPORT_ROOT, "browser_ui_smoke.json");
const LIVE_STATE_PATH = path.join(ROOT, "Data", "runtime", "kira_world_shell_state.json");
const CANDIDATES = [
  { id: "elsa_frozen_frozen_fever_frozen_ii_20260716", label: "Elsa (Frozen through Frozen II)" },
  { id: "kathryn_merteuil_kathryn_merteuil_20260605_213017", label: "Kathryn Merteuil" },
];

function sha256OrNull(filePath) {
  return fs.existsSync(filePath)
    ? crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex")
    : null;
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

async function waitForHttp(url, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.status < 500) return;
    } catch (_error) {
      // The isolated process can take a moment to import its candidate catalog.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function portReachable(port, timeoutMs = 500) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: "127.0.0.1", port });
    const finish = (value) => {
      socket.destroy();
      resolve(value);
    };
    socket.setTimeout(timeoutMs);
    socket.once("connect", () => finish(true));
    socket.once("timeout", () => finish(false));
    socket.once("error", () => finish(false));
  });
}

async function standardLauncherProbe() {
  const reachable = await portReachable(8768);
  if (!reachable) return { reachable: false, port: 8768 };
  try {
    const response = await fetch("http://127.0.0.1:8768/api/state", { signal: AbortSignal.timeout(1_500) });
    const state = await response.json();
    const records = Object.fromEntries(
      (state.candidates || [])
        .filter((item) => CANDIDATES.some((expected) => expected.id === item.id))
        .map((item) => [item.id, {
          conversation_mode: item.conversation_mode,
          activatable: item.activatable,
          voice_allowed: item.voice_allowed,
        }]),
    );
    return { reachable: true, port: 8768, http_status: response.status, records };
  } catch (error) {
    return { reachable: true, port: 8768, error: error.message };
  }
}

function waitForExit(child, timeoutMs = 8_000) {
  if (child.exitCode !== null) return Promise.resolve(child.exitCode);
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), timeoutMs);
    child.once("exit", (code) => {
      clearTimeout(timer);
      resolve(code);
    });
  });
}

fs.mkdirSync(REPORT_ROOT, { recursive: true });
const isolatedRuntime = fs.mkdtempSync(path.join(os.tmpdir(), "kira-text-voice-smoke-"));
const liveStateHashBefore = sha256OrNull(LIVE_STATE_PATH);
const standardLauncherBefore = await standardLauncherProbe();
const port = await freePort();
const baseUrl = `http://127.0.0.1:${port}/`;
const child = spawn(
  "python",
  ["tools/kira_text_voice_profiles_isolated_server.py", "--port", String(port), "--runtime", isolatedRuntime],
  { cwd: ROOT, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
);
let childOutput = "";
child.stdout.on("data", (chunk) => { childOutput = `${childOutput}${chunk}`.slice(-16_000); });
child.stderr.on("data", (chunk) => { childOutput = `${childOutput}${chunk}`.slice(-16_000); });

let browser = null;
let fatalError = null;
const results = [];
const diagnostics = { page_errors: [], console_errors: [], requests: [], media_play_calls: 0 };

try {
  await waitForHttp(`${baseUrl}api/state`);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.addInitScript(() => {
    window.__isolatedMediaPlayCalls = 0;
    const original = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function isolatedNoPlayback() {
      window.__isolatedMediaPlayCalls += 1;
      return Promise.reject(new Error("Audio playback disabled by isolated launcher smoke"));
    };
    window.__originalMediaPlay = original;
  });
  page.on("pageerror", (error) => diagnostics.page_errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.console_errors.push(message.text());
  });
  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (["/api/activate", "/api/chat", "/api/deactivate"].includes(pathname)) {
      diagnostics.requests.push({ pathname, method: request.method(), body: request.postDataJSON() });
    }
  });

  // The shell deliberately polls state, so networkidle is not a valid readiness
  // signal. DOMContentLoaded plus the candidate-option assertion below is.
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForFunction((ids) => {
    const values = [...document.querySelectorAll("#candidate option")].map((option) => option.value);
    return ids.every((id) => values.includes(id));
  }, CANDIDATES.map((item) => item.id), { timeout: 30_000 });

  for (const expected of CANDIDATES) {
    await page.selectOption("#candidate", expected.id);
    const before = await page.evaluate((candidateId) => {
      const option = [...document.querySelectorAll("#candidate option")].find((item) => item.value === candidateId);
      const button = document.querySelector("#activate");
      const review = document.querySelector("#candidateReviewReason");
      return {
        option_text: option?.textContent || "",
        activate_text: button?.textContent || "",
        activate_disabled: !!button?.disabled,
        bounded_review_visible: review ? !review.hidden : null,
        bounded_review_text: review?.textContent || "",
      };
    }, expected.id);

    const activationResponsePromise = page.waitForResponse((response) =>
      response.url().endsWith("/api/activate") && response.request().method() === "POST",
    );
    await page.locator("#activate").click();
    const activationResponse = await activationResponsePromise;
    const activationBody = await activationResponse.json();
    await page.waitForFunction((candidateId) => {
      const status = document.querySelector("#status")?.textContent || "";
      const deactivate = document.querySelector("#deactivate");
      return status.includes("Active:") && !status.includes("Active: none")
        && deactivate?.textContent === "Deactivate" && !deactivate.disabled
        && document.querySelector("#candidate")?.value === candidateId;
    }, expected.id, { timeout: 10_000 });
    const activeState = await page.evaluate(async () => (await fetch("/api/state")).json());
    const activeAudit = await page.evaluate(async () => (await fetch("/__test/audit")).json());

    const chatResponsePromise = page.waitForResponse((response) =>
      response.url().endsWith("/api/chat") && response.request().method() === "POST",
    );
    await page.locator("#chatText").fill("Please confirm this isolated voice queue test.");
    await page.locator("#chatForm button").click();
    const chatResponse = await chatResponsePromise;
    const chatBody = await chatResponse.json();
    await page.waitForFunction(() => document.querySelector("#chatForm button")?.textContent === "Send", null, { timeout: 10_000 });
    const queuedAudit = await page.evaluate(async () => (await fetch("/__test/audit")).json());
    const queuedVoice = [...(queuedAudit.voice_queue_captures || [])].reverse()
      .find((item) => item.candidate === expected.id) || null;

    const deactivationResponsePromise = page.waitForResponse((response) =>
      response.url().endsWith("/api/deactivate") && response.request().method() === "POST",
    );
    await page.locator("#deactivate").click();
    const deactivationResponse = await deactivationResponsePromise;
    const deactivationBody = await deactivationResponse.json();
    await page.waitForFunction(() => {
      const button = document.querySelector("#deactivate");
      return button?.textContent === "Nothing active" && button.disabled;
    }, null, { timeout: 10_000 });
    const inactiveAudit = await page.evaluate(async () => (await fetch("/__test/audit")).json());

    results.push({
      candidate: expected.id,
      expected_label: expected.label,
      before,
      activation: {
        http_status: activationResponse.status(),
        body: activationBody,
        active_candidate: activeState.active_candidate,
        active_label: activeState.active_label,
        active_conversation_mode: activeState.active_conversation_mode,
        voice_status: activeState.voice_status,
        text_voice_mode: activeState.text_voice_mode,
        world_url: activeState.world_url,
        avatar_url: activeState.avatar_url,
        voice_session_token: activeAudit.voice_session_token,
        runtime_update_calls: activeAudit.update_calls,
      },
      send: {
        http_status: chatResponse.status(),
        active_label: chatBody.active_label,
        voice_result: chatBody.voice_result,
        queued_voice: queuedVoice,
        runtime_update_calls: queuedAudit.update_calls,
      },
      deactivation: {
        http_status: deactivationResponse.status(),
        body: deactivationBody,
        active_candidate: inactiveAudit.state.active_candidate,
        active_conversation_mode: inactiveAudit.state.active_conversation_mode,
        sentinel: inactiveAudit.state.owner_test_sentinel,
        saved_kira_position: inactiveAudit.state.last_avatar_positions?.kira || null,
      },
    });
  }

  diagnostics.media_play_calls = await page.evaluate(() => Number(window.__isolatedMediaPlayCalls || 0));
} catch (error) {
  fatalError = error.stack || error.message;
} finally {
  if (browser) await browser.close();
  try {
    await fetch(`${baseUrl}__test/shutdown`, { method: "POST", signal: AbortSignal.timeout(2_000) });
  } catch (_error) {
    // The exact isolated child is terminated below if graceful shutdown failed.
  }
  const gracefulExit = await waitForExit(child, 5_000);
  if (gracefulExit === null && child.exitCode === null) child.kill();
  await waitForExit(child, 5_000);
}

const isolatedServerStillReachable = await portReachable(port);
const liveStateHashAfter = sha256OrNull(LIVE_STATE_PATH);
const standardLauncherAfter = await standardLauncherProbe();
const candidateChecks = results.map((result) => ({
  candidate: result.candidate,
  authored_name_stable: result.before.option_text.startsWith(result.expected_label)
    && result.activation.body?.label === result.expected_label
    && result.activation.active_label === result.expected_label
    && result.send.active_label === result.expected_label
    && !result.before.option_text.includes(result.candidate),
  normal_activate_button: result.before.activate_text === "Activate AI"
    && !result.before.activate_disabled
    && !result.before.bounded_review_visible,
  normal_active_voice_session: result.activation.http_status === 200
    && result.activation.active_candidate === result.candidate
    && result.activation.active_conversation_mode === "normal"
    && result.activation.text_voice_mode === true
    && result.activation.world_url === ""
    && result.activation.avatar_url === ""
    && result.activation.voice_session_token > 0,
  own_voice_queued_without_playback: result.send.http_status === 200
    && ["queued_async_voice", "queued_behind_previous_voice"].includes(result.send.voice_result?.reason)
    && result.send.queued_voice?.candidate === result.candidate
    && result.send.queued_voice?.label === result.expected_label
    && result.send.queued_voice?.engine === "chatterbox_tts"
    && result.send.queued_voice?.required_reference === true
    && result.send.queued_voice?.binding_ready === true
    && result.send.queued_voice?.generic_fallback_blocked === true
    && result.send.queued_voice?.reference_exists === true
    && result.send.queued_voice?.audio_generated === false
    && result.send.queued_voice?.audio_played === false,
  clean_inactive_deactivation: result.deactivation.http_status === 200
    && result.deactivation.active_candidate === ""
    && result.deactivation.active_conversation_mode === ""
    && result.deactivation.sentinel === "preserve-me"
    && result.deactivation.saved_kira_position?.position?.x === 1.25,
  no_embodied_runtime_state_write: (result.activation.runtime_update_calls || []).length === 0
    && (result.send.runtime_update_calls || []).length === 0,
}));
const references = results.map((result) => result.send.queued_voice?.reference_audio || "").filter(Boolean);
const checks = {
  both_profiles_exercised: results.length === CANDIDATES.length,
  each_profile_passed_ui_activation_queue_deactivation: candidateChecks.length === CANDIDATES.length
    && candidateChecks.every((record) => Object.entries(record).filter(([key]) => key !== "candidate").every(([, value]) => value)),
  profiles_use_distinct_own_reference_files: references.length === CANDIDATES.length && new Set(references).size === CANDIDATES.length,
  no_audio_play_or_generation: diagnostics.media_play_calls === 0
    && results.every((result) => !result.send.queued_voice?.audio_played && !result.send.queued_voice?.audio_generated),
  no_3d_world_or_avatar_started: results.every((result) => result.activation.world_url === "" && result.activation.avatar_url === ""),
  real_saved_state_unchanged: liveStateHashBefore === liveStateHashAfter,
  isolated_server_stopped: !isolatedServerStillReachable,
  no_browser_errors: diagnostics.page_errors.length === 0 && diagnostics.console_errors.length === 0,
  no_fatal_error: fatalError === null,
};
const standardModes = standardLauncherAfter.records || standardLauncherBefore.records || {};
const standardLooksStale = CANDIDATES.some((candidate) =>
  standardModes[candidate.id] && standardModes[candidate.id].conversation_mode !== "normal",
);
const staleLauncherRisk = standardLauncherAfter.reachable || standardLauncherBefore.reachable
  ? {
      level: standardLooksStale ? "confirmed_stale_standard_server_or_cached_window" : "possible_cached_window",
      note: standardLooksStale
        ? "Port 8768 is serving old Elsa/Kathryn policy. Close the old launcher and start it again so --takeover loads current code."
        : "A launcher is already open on port 8768. Its page can retain old JavaScript until the window is closed/reopened or hard-refreshed.",
    }
  : {
      level: "low_on_next_clean_launch",
      note: "No standard launcher was listening during the smoke. The next clean Start_Kira_Text_Voice_Chat launch will load current code.",
    };
const report = {
  schema_version: 1,
  generated_at: new Date().toISOString(),
  status: Object.values(checks).every(Boolean) ? "passed" : "failed_or_incomplete",
  isolation: {
    random_port: port,
    runtime_directory: isolatedRuntime,
    audio_worker_disabled: true,
    audio_playback_disabled_in_browser: true,
    world_processes_started: false,
    live_state_path: path.relative(ROOT, LIVE_STATE_PATH).replaceAll("\\", "/"),
    live_state_sha256_before: liveStateHashBefore,
    live_state_sha256_after: liveStateHashAfter,
  },
  checks,
  candidate_checks: candidateChecks,
  results,
  stale_launcher_risk: staleLauncherRisk,
  standard_launcher_before: standardLauncherBefore,
  standard_launcher_after: standardLauncherAfter,
  diagnostics,
  fatal_error: fatalError,
  isolated_server_output_tail: childOutput,
};
fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify({ status: report.status, checks, candidateChecks, staleLauncherRisk, standardLauncherBefore, standardLauncherAfter, fatalError }, null, 2)}\n`);
if (report.status !== "passed") process.exitCode = 1;
