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

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(typeof address === "object" && address ? address.port : 0));
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
      // Vite is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 120));
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

const evidence = {
  generated_at: new Date().toISOString(),
  incident: "2026-07-19 06:51 kitchen coffee route stopped at the TV",
  mode: "headless_body_marker_only_no_mind_no_voice_no_persistence",
  checks: {},
};
let vite = null;
let browser = null;
let fatalError = null;

try {
  const port = await freePort();
  const viteEntry = path.join(PREVIEW_ROOT, "node_modules", "vite", "bin", "vite.js");
  vite = spawn(process.execPath, [viteEntry, "--host", "127.0.0.1", "--port", String(port), "--strictPort"], {
    cwd: PREVIEW_ROOT,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
  const url = `http://127.0.0.1:${port}/?area=home&kitchenNavigationSmoke=20260719`;
  await waitForHttp(url);
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-angle=swiftshader"],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForFunction(() => Boolean(window.kiraHomeWorldDebug?.planOneBedroomInteriorRoute), null, { timeout: 120_000 });

  const result = await page.evaluate(() => {
    const debug = window.kiraHomeWorldDebug;
    debug.injectShellState({
      active_candidate: "kira",
      active_label: "Kira",
      active_ai: "Kira",
      active_action: "idle",
      active_model_url: "",
      active_pose_manifest_url: "",
      active_body_selection: { enforced: true, valid: false, reason: "navigation_smoke_body_marker_only" },
      location: "home",
      isolated_browser_test: true,
      do_not_persist: true,
    });
    // Exact coordinate recorded at the end of the original deterministic
    // route smoke.  It is beside the real coffee station and physically in
    // the right/rear kitchen, never the outdoor Home World ground area.
    debug.setActiveAvatarPosition({ x: -17.983, y: 0.05, z: 0.082, roamZone: "kira_home_world" });
    const exactFinalCoordinatePlace = debug.currentPlace();
    debug.setActiveAvatarPosition({ x: -18.301, y: 0.05, z: 2.634, roamZone: "kira_home_world" });

    const noToolProjectTruth = debug.activityTruth("project_work");
    const plan = debug.planOneBedroomInteriorRoute({
      start: { x: -18.301, y: 0.05, z: 2.634 },
      goal: { x: -17.95, y: 0.05, z: -0.22 },
    });
    const started = debug.startHomeKitchenCoffeeForTest({ seconds: 12 });
    const routeBeforeEquivalentIntent = debug.activeHomeRouteProgress();
    const equivalentIntentAccepted = debug.publishPersonOwnedBodyIntentForTest("get_drink");
    const routeAfterEquivalentIntent = debug.activeHomeRouteProgress();
    // One continuous simulated interval is intentional: the debug clock is
    // sampled once per call, while this helper advances its own deterministic
    // time inside the call.
    const stepped = debug.stepActiveAvatarForTest(12, 600);
    return {
      exactFinalCoordinatePlace,
      noToolProjectTruth,
      plan,
      started,
      equivalentIntentAccepted,
      routeBeforeEquivalentIntent,
      routeAfterEquivalentIntent,
      stepped,
      final: debug.activeHomeRouteProgress(),
      coffeeTruth: debug.activityTruth("drink_coffee"),
    };
  });

  evidence.result = result;
  const samples = (result.stepped?.motionSafety?.positionSamples || []).map((sample) => ({
    x: sample.x,
    y: sample.y,
    z: sample.z,
  }));
  const totalPathMeters = samples.reduce((sum, point, index) => {
    if (!index) return sum;
    return sum + Math.hypot(point.x - samples[index - 1].x, point.z - samples[index - 1].z);
  }, 0);
  const maxDistanceFromStart = samples.reduce(
    (max, point) => Math.max(max, Math.hypot(point.x + 18.301, point.z - 2.634)),
    0,
  );
  const reachedInteraction = result.final.interaction?.id === "autonomous_kitchen_coffee";
  evidence.measurements = {
    totalPathMeters: Number(totalPathMeters.toFixed(3)),
    maxDistanceFromStart: Number(maxDistanceFromStart.toFixed(3)),
    finalBody: result.final.body,
  };
  evidence.checks.direct_path_reproduces_tv_obstruction = result.plan.directPathClear === false;
  evidence.checks.actual_world_planner_found_detour = result.plan.ok === true && result.plan.waypoints.length >= 2;
  evidence.checks.route_started_from_person_owned_intent = result.started === true
    && result.routeBeforeEquivalentIntent.route?.personOwnedIntent === true;
  evidence.checks.equivalent_intent_did_not_restart_route = result.equivalentIntentAccepted === true
    && result.routeAfterEquivalentIntent.route?.id === result.routeBeforeEquivalentIntent.route?.id
    && result.routeAfterEquivalentIntent.route?.coalescedIntentCount === 1;
  evidence.checks.body_moved_around_tv = maxDistanceFromStart > 2.0 && totalPathMeters > 2.0;
  evidence.checks.no_collider_penetration = result.stepped.motionSafety.colliderPenetrationSamples === 0;
  evidence.checks.reached_real_coffee_affordance = reachedInteraction && result.coffeeTruth.grounded === true;
  evidence.checks.exact_final_coordinate_is_inside_kitchen = result.exactFinalCoordinatePlace?.label === "Kira one-bedroom kitchen"
    && result.exactFinalCoordinatePlace?.inside === true
    && result.exactFinalCoordinatePlace?.outside === false
    && result.exactFinalCoordinatePlace?.canGetCoffeeHere === true;
  evidence.checks.runtime_final_place_is_inside_kitchen = result.stepped?.motionSafety?.currentPlace?.label === "Kira one-bedroom kitchen"
    && result.stepped?.motionSafety?.currentPlace?.inside === true
    && result.stepped?.motionSafety?.currentPlace?.outside === false;
  evidence.checks.empty_handed_project_claim_not_grounded = result.noToolProjectTruth.grounded === false
    && result.noToolProjectTruth.activeUse === false;
  evidence.checks.no_route_failure_or_teleport = !result.final.failure
    && result.routeBeforeEquivalentIntent.route?.teleported !== true
    && result.routeAfterEquivalentIntent.route?.teleported !== true;
} catch (error) {
  fatalError = error?.stack || error?.message || String(error);
} finally {
  if (browser) await browser.close();
  await stopChild(vite);
}

evidence.fatal_error = fatalError;
evidence.status = !fatalError && Object.values(evidence.checks).every(Boolean) ? "passed" : "failed";
const stamp = evidence.generated_at.replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
const reportDir = path.join(ROOT, "Data", "world_tests", "kira_kitchen_navigation_20260719", stamp);
fs.mkdirSync(reportDir, { recursive: true });
const reportPath = path.join(reportDir, "evidence.json");
fs.writeFileSync(reportPath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");

process.stdout.write(`${JSON.stringify({
  status: evidence.status,
  report: path.relative(ROOT, reportPath).replaceAll("\\", "/"),
  checks: evidence.checks,
  measurements: evidence.measurements || null,
  fatal_error: fatalError,
}, null, 2)}\n`);
if (evidence.status !== "passed") process.exitCode = 1;
