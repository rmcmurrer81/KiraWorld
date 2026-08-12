import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "../Avatar/runtime3d/node_modules/playwright/index.mjs";

function option(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

function required(name) {
  const value = option(name);
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const url = required("--url");
const reportPath = required("--report");
const screenshotPath = required("--screenshot");
const packagePath = required("--package");
const bookmarkDir = required("--bookmark-dir");
const truthPanelPath = option(
  "--truth-panel",
  path.join(path.dirname(screenshotPath), `${path.basename(screenshotPath, path.extname(screenshotPath))}_truth_panel.png`),
);
const bookmarkPanelPath = option(
  "--bookmark-panel",
  path.join(path.dirname(screenshotPath), `${path.basename(screenshotPath, path.extname(screenshotPath))}_bookmark_panel.png`),
);
const entranceDoorPath = option(
  "--entrance-door",
  path.join(path.dirname(screenshotPath), `${path.basename(screenshotPath, path.extname(screenshotPath))}_approximate_entrance.png`),
);
const circulationPath = option(
  "--circulation",
  path.join(path.dirname(screenshotPath), `${path.basename(screenshotPath, path.extname(screenshotPath))}_approximate_circulation.png`),
);
const diagnostics = { page_errors: [], console_errors: [], request_failures: [], http_errors: [] };
let browser;
let report = { schema_version: 1, status: "failed", url, diagnostics };

try {
  const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const launchOptions = {
    headless: true,
    args: ["--use-angle=default", "--enable-webgl", "--disable-background-timer-throttling"],
  };
  if (process.platform === "win32" && fs.existsSync(edge)) launchOptions.executablePath = edge;
  browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on("pageerror", (error) => diagnostics.page_errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.console_errors.push(message.text());
  });
  page.on("requestfailed", (request) => diagnostics.request_failures.push(`${request.url()} :: ${request.failure()?.errorText || "failed"}`));
  page.on("response", (response) => {
    if (response.status() >= 400) diagnostics.http_errors.push(`${response.status()} ${response.url()}`);
  });

  await page.goto(url, { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForFunction(() => window.__previewReady === true, null, { timeout: 120000 });
  const state = await page.evaluate(async () => {
    const debug = window.__louvreNotebookDebug;
    await debug.waitForStreamingIdle();
    const initialStreaming = debug.streamingSnapshot();
    const routeChecks = debug.runStaticRouteChecks();
    const primaryRoute = debug.contract.routes[0];
    const routeMeasurements = {
      start: debug.measureRouteAt(primaryRoute, 0, 62),
      finish: debug.measureRouteAt(primaryRoute, 0, 22.5),
    };
    const collisionProbes = {
      main_pyramid: debug.blocked(0, 0),
      west_pool: debug.blocked(-45, -2),
      clear_arrival: debug.blocked(0, 62),
    };
    const blockedMoveAccepted = debug.attemptWalkPosition(0, 0);
    const safeMoveAccepted = debug.setWalkPosition(0, 62);
    const routeSelected = debug.setRoute(0);
    const arrivalBookmarkSelected = debug.setBookmark("arrival_scale");
    const arrivalBookmarkSnapshot = debug.getSnapshot();
    const entranceBookmarkSelected = debug.setBookmark("entrance_human");
    const entranceBookmarkSnapshot = debug.getSnapshot();
    const screenshotBookmarkSelected = debug.setBookmark("two_small_pyramids");
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

    const doorApproachStreaming = await debug.requestStreamingAt(0, 1.68, 17);
    const closedThresholdCrossing = debug.attemptApproximateThresholdCrossing();
    const doorOpenRequested = await debug.setApproximateEntranceOpen(true);
    const doorReachedOpen = await debug.waitForEntrancePhase("open", 8000);
    const openDoorState = debug.entranceSnapshot();
    const openThresholdCrossing = debug.attemptApproximateThresholdCrossing();
    const stairDown = debug.walkApproximateSpiral("down", 40);
    const stairUp = debug.walkApproximateSpiral("up", 40);
    const runtimeObjectCounts = debug.runtimeObjectCounts();
    const escalatorSurfaceBlocked = debug.escalatorSurfaceProbe() === null;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const rendererMetrics = debug.rendererMetrics();
    const farStreaming = await debug.requestStreamingAt(0, 1.68, 84);
    const reloadApproachStreaming = await debug.requestStreamingAt(0, 1.68, 17);
    const restoredDoorBeforeDestination = debug.entranceSnapshot();
    const restoredDestinationRequested = await debug.setApproximateEntranceOpen(true);
    const restoredReadyStreaming = debug.streamingSnapshot();
    const restoredDoorAfterDestination = debug.entranceSnapshot();
    const streamingFailureProbes = await debug.streamingFailureProbes();
    debug.setBookmark("two_small_pyramids");
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    return {
      world_id: debug.worldId,
      location_id: debug.locationId,
      build_id: debug.buildId,
      status: debug.status,
      solo_review_only: debug.soloReviewOnly,
      temporary_ai_activation_allowed: debug.temporaryAiActivationAllowed,
      people_loaded: debug.peopleLoaded,
      minds_loaded: debug.mindsLoaded,
      voice_loaded: debug.voiceLoaded,
      ollama_loaded: debug.ollamaLoaded,
      home_world_loaded: debug.homeWorldLoaded,
      home_world_mutation_allowed: debug.homeWorldMutationAllowed,
      strip_mall_mutation_allowed: debug.stripMallMutationAllowed,
      runtime_registered: debug.runtimeRegistered,
      interior_enabled: debug.interiorEnabled,
      bounded_approximate_circulation_owner_review_enabled: debug.boundedApproximateCirculationOwnerReviewEnabled,
      full_louvre_interior_enabled: debug.fullLouvreInteriorEnabled,
      elevators_enabled: debug.elevatorsEnabled,
      gallery_enabled: debug.galleryEnabled,
      artwork_enabled: debug.artworkEnabled,
      eye_height_m: debug.eyeHeightM,
      collider_count: debug.colliderCount,
      route_count: debug.routeCount,
      landmark_count: debug.landmarkCount,
      bookmark_count: debug.bookmarkCount,
      truth_marker_count: debug.truthMarkerCount,
      smaller_pyramid_count: debug.smallerPyramidCount,
      streaming: initialStreaming,
      door_approach_streaming: doorApproachStreaming,
      circulation_interactions: {
        closed_threshold_crossing: closedThresholdCrossing,
        door_open_requested: doorOpenRequested,
        door_reached_open: doorReachedOpen,
        open_door_state: openDoorState,
        open_threshold_crossing: openThresholdCrossing,
        stair_down: stairDown,
        stair_up: stairUp,
        runtime_object_counts: runtimeObjectCounts,
        escalator_surface_blocked: escalatorSurfaceBlocked,
        renderer_metrics: rendererMetrics,
        far_streaming: farStreaming,
        reload_approach_streaming: reloadApproachStreaming,
        restored_door_before_destination: restoredDoorBeforeDestination,
        restored_destination_requested: restoredDestinationRequested,
        restored_ready_streaming: restoredReadyStreaming,
        restored_door_after_destination: restoredDoorAfterDestination,
        streaming_failure_probes: streamingFailureProbes,
      },
      route_checks: routeChecks,
      route_measurements: routeMeasurements,
      collision_probes: collisionProbes,
      movement_probes: { blocked_move_accepted: blockedMoveAccepted, safe_move_accepted: safeMoveAccepted },
      route_selected: routeSelected,
      bookmark_probes: {
        arrival_selected: arrivalBookmarkSelected,
        arrival_snapshot: arrivalBookmarkSnapshot,
        entrance_selected: entranceBookmarkSelected,
        entrance_snapshot: entranceBookmarkSnapshot,
        screenshot_selected: screenshotBookmarkSelected,
      },
      snapshot: debug.getSnapshot(),
      truth_chip_count: document.querySelectorAll(".truth-chip").length,
      feedback_panel_present: Boolean(document.getElementById("feedbackPanel")),
      bookmark_panel_present: Boolean(document.getElementById("bookmarkPanel")),
      bookmark_option_count: document.querySelectorAll("#bookmarkSelect option").length,
      bookmark_link: document.getElementById("bookmarkLink")?.value || "",
      route_metric_text: document.getElementById("routeMetric")?.textContent || "",
      collision_metric_text: document.getElementById("collisionMetric")?.textContent || "",
      actor_mesh_count: [...document.querySelectorAll("canvas")].length ? 0 : -1,
    };
  });

  fs.mkdirSync(path.dirname(entranceDoorPath), { recursive: true });
  await page.evaluate(async () => {
    const debug = window.__louvreNotebookDebug;
    await debug.requestStreamingAt(0, 1.68, 17);
    await debug.waitForStreamingIdle();
    await debug.setApproximateEntranceOpen(true);
    const opened = await debug.waitForEntrancePhase("open", 8000);
    if (!opened || !debug.entranceSnapshot().threshold_passable) {
      throw new Error("Bounded circulation cells were not ready for review screenshots");
    }
  });
  await page.evaluate(() => window.__louvreNotebookDebug.setCirculationReviewView("entrance"));
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const entranceDoorScreenshot = await page.screenshot({ path: entranceDoorPath });
  await page.evaluate(() => window.__louvreNotebookDebug.setCirculationReviewView("stair"));
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const circulationScreenshot = await page.screenshot({ path: circulationPath });
  await page.evaluate(() => window.__louvreNotebookDebug.setBookmark("two_small_pyramids"));
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));

  await page.locator("#feedbackToggle").click();
  await page.locator("#feedbackCategory").selectOption("navigation");
  await page.locator("#feedbackVerdict").selectOption("works");
  await page.locator("#feedbackNote").fill("Automated smoke: feedback storage and route context are available.");
  await page.locator("#feedbackSave").click();
  const feedbackState = await page.evaluate(() => ({
    entries: window.__louvreNotebookDebug.feedbackEntries(),
    status: document.getElementById("feedbackStatus")?.textContent || "",
  }));

  fs.mkdirSync(path.dirname(packagePath), { recursive: true });
  const [packageDownload] = await Promise.all([
    page.waitForEvent("download", { timeout: 120000 }),
    page.locator("#reviewPackageExport").click(),
  ]);
  await packageDownload.saveAs(packagePath);
  const packagePayload = JSON.parse(fs.readFileSync(packagePath, "utf8"));
  const captureBytes = Buffer.from(packagePayload.capture.data_url.split(",", 2)[1], "base64");
  const packageCaptureHash = crypto.createHash("sha256").update(captureBytes).digest("hex");
  const packageState = {
    suggested_filename: packageDownload.suggestedFilename(),
    package_kind: packagePayload.package_kind,
    build_id: packagePayload.build_id,
    server_write_enabled: packagePayload.server_write_enabled,
    active_bookmark_id: packagePayload.reproducible_review.active_bookmark_id,
    active_route_id: packagePayload.reproducible_review.active_route_id,
    feedback_count: packagePayload.feedback_entries.length,
    collision_events: packagePayload.measurements.collision_events,
    capture_bytes: captureBytes.length,
    capture_sha256: packagePayload.capture.sha256,
    computed_capture_sha256: packageCaptureHash,
    contract_bookmark_count: packagePayload.source_and_isolation_contract.review_bookmarks.length,
  };
  await page.locator("#feedbackClose").click();

  fs.mkdirSync(bookmarkDir, { recursive: true });
  const bookmarkDefinitions = await page.evaluate(() => window.__louvreNotebookDebug.contract.review_bookmarks);
  const bookmarkScreenshots = [];
  for (const [index, bookmark] of bookmarkDefinitions.entries()) {
    const selected = await page.evaluate((bookmarkId) => window.__louvreNotebookDebug.setBookmark(bookmarkId), bookmark.id);
    assert(selected, `Could not select bookmark ${bookmark.id} for screenshot evidence`);
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const bookmarkPath = path.join(bookmarkDir, `${String(index + 1).padStart(2, "0")}_${bookmark.id}.png`);
    const bytes = await page.screenshot({ path: bookmarkPath });
    bookmarkScreenshots.push({
      id: bookmark.id,
      label: bookmark.label,
      path: bookmarkPath,
      bytes: bytes.length,
      sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
    });
  }
  await page.evaluate(() => window.__louvreNotebookDebug.setBookmark("two_small_pyramids"));

  const renderSample = await page.evaluate(async () => {
    const canvas = document.getElementById("world");
    let frames = 0;
    await new Promise((resolve) => {
      const start = performance.now();
      function tick(now) {
        frames += 1;
        if (now - start >= 750) resolve();
        else requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    const colors = new Set();
    let opaque = 0;
    if (gl && canvas.width > 0 && canvas.height > 0) {
      const pixels = new Uint8Array(canvas.width * canvas.height * 4);
      gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      const stride = Math.max(1, Math.floor((canvas.width * canvas.height) / 2048));
      for (let pixel = 0; pixel < canvas.width * canvas.height; pixel += stride) {
        const index = pixel * 4;
        colors.add(`${pixels[index]},${pixels[index + 1]},${pixels[index + 2]},${pixels[index + 3]}`);
        if (pixels[index + 3] > 0) opaque += 1;
      }
    }
    return { canvas: { width: canvas.width, height: canvas.height }, frames, unique_rgba_samples: colors.size, opaque_samples: opaque };
  });

  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.waitForTimeout(180);
  fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
  const screenshot = await page.screenshot({ path: screenshotPath });
  const truthPanel = await page.locator("#truthPanel").screenshot({ path: truthPanelPath });
  const bookmarkPanel = await page.locator("#bookmarkPanel").screenshot({ path: bookmarkPanelPath });

  assert(state.status === "prototype_draft_not_final_not_approved", "Preview overclaims approval/finality");
  assert(state.solo_review_only === true, "Solo mode is not active");
  assert(state.temporary_ai_activation_allowed === false, "TemporaryAI activation became allowed");
  assert(state.people_loaded === 0 && state.minds_loaded === 0, "A person or mind was loaded");
  assert(state.voice_loaded === false && state.ollama_loaded === false, "Voice or Ollama was loaded");
  assert(state.home_world_loaded === false && state.home_world_mutation_allowed === false, "Home World was loaded or mutable");
  assert(state.strip_mall_mutation_allowed === false && state.runtime_registered === false, "Protected runtime state changed");
  assert(state.interior_enabled === false && state.full_louvre_interior_enabled === false, "A full/unsourced Louvre interior became enabled");
  assert(state.bounded_approximate_circulation_owner_review_enabled === true, "The bounded circulation owner-review capability is missing");
  assert(state.elevators_enabled === false && state.gallery_enabled === false && state.artwork_enabled === false, "An elevator, gallery, or artwork runtime became enabled");
  assert(state.streaming?.contract_status === "streaming_scaffold_only_not_complete", "Streaming scaffold truth status is missing");
  assert(JSON.stringify(state.streaming?.managed_loaded_cells) === JSON.stringify(["cour_napoleon_exterior"]), "Arrival should keep only the exterior cell resident");
  assert(state.streaming?.transactional_preload_before_unload === true && state.streaming?.state_preserved_across_reload === true, "Transactional/state-preserving streaming guarantees are missing");
  assert(JSON.stringify(state.streaming?.interest?.desired_cells) === JSON.stringify(["cour_napoleon_exterior"]), "Courtyard interest plan selected an unsupported cell");
  assert(state.streaming?.interior_complete === false && state.streaming?.gallery_rooms_proven === false && state.streaming?.artwork_proven === false, "Streaming scaffold promoted unsupported Louvre content");
  assert(JSON.stringify(state.door_approach_streaming?.managed_loaded_cells) === JSON.stringify(["cour_napoleon_exterior", "pyramid_entrance_transition"]), "Distance alone should not load the portal-gated descent cell");
  const interactions = state.circulation_interactions;
  assert(interactions.closed_threshold_crossing.accepted === false, "Closed approximate door failed to block threshold crossing");
  assert(interactions.door_open_requested && interactions.door_reached_open, "Approximate entrance did not open after destination validation");
  assert(interactions.open_door_state.threshold_passable === true && interactions.open_door_state.threshold_collision_solid === false, "Open door collision state is inconsistent");
  assert(interactions.open_threshold_crossing.accepted === true, "Validated open threshold did not admit the owner-review camera");
  assert(interactions.stair_down.every((item) => item.accepted), "The approximate spiral descent contains a rejected sample");
  assert(interactions.stair_up.every((item) => item.accepted), "The approximate spiral return contains a rejected sample");
  assert(interactions.stair_down[0].floor_y_m === 0 && interactions.stair_down.at(-1).floor_y_m === -8, "Spiral descent endpoints drifted");
  assert(interactions.stair_down.every((item, index, values) => index === 0 || item.floor_y_m <= values[index - 1].floor_y_m + 0.001), "Spiral descent height is not monotonic");
  assert(interactions.stair_up.every((item, index, values) => index === 0 || item.floor_y_m >= values[index - 1].floor_y_m - 0.001), "Spiral return height is not monotonic");
  assert(interactions.runtime_object_counts.elevator === 0 && interactions.runtime_object_counts.gallery === 0 && interactions.runtime_object_counts.artwork === 0, "Unsupported elevator/gallery/artwork objects entered the runtime");
  assert(interactions.runtime_object_counts.escalator === 2 && interactions.escalator_surface_blocked, "Escalator forms must be visible-only and non-walkable");
  assert(JSON.stringify(interactions.far_streaming.managed_loaded_cells) === JSON.stringify(["cour_napoleon_exterior"]), "Far return did not unload both bounded interior cells");
  assert(interactions.far_streaming.persistent_state_cells.includes("pyramid_entrance_transition") && interactions.far_streaming.persistent_state_cells.includes("under_pyramid_level_minus_2_circulation"), "Unload did not persist entrance/circulation state");
  assert(interactions.far_streaming.portal_authorized_cells.length === 0, "Portal authorization did not expire on unload");
  assert(JSON.stringify(interactions.reload_approach_streaming.managed_loaded_cells) === JSON.stringify(["cour_napoleon_exterior", "pyramid_entrance_transition"]), "Reload approach bypassed the portal authorization gate");
  assert(interactions.restored_door_before_destination.progress === 1 && interactions.restored_door_before_destination.threshold_passable === false, "Door state did not restore safely while destination was absent");
  assert(interactions.restored_destination_requested && interactions.restored_door_after_destination.threshold_passable === true, "Restored door did not regain passability after destination reload");
  assert(interactions.restored_ready_streaming.managed_loaded_cells.length === 3, "Restored bounded circulation set is incomplete");
  for (const probe of Object.values(interactions.streaming_failure_probes)) {
    assert(probe.snapshot.transaction.ok === false, "An intentional streaming failure was not blocked");
    assert(probe.snapshot.transaction.phase === "blocked_before_source_unload", "A failure crossed the atomic source-unload boundary");
    assert(probe.snapshot.managed_loaded_cells.includes("cour_napoleon_exterior"), "A failure discarded the last proven exterior cell");
  }
  assert(interactions.streaming_failure_probes.budget_overrun.counters.disposed >= 1, "Budget-overrun staging did not dispose rejected work");
  assert(interactions.streaming_failure_probes.commit_failure.counters.disposed >= 2, "Commit rollback did not dispose all staged modules");
  assert(interactions.streaming_failure_probes.unload_preflight_failure.snapshot.managed_loaded_cells.length === 3, "Unload preflight failure did not retain its last proven set");
  const activeBudget = state.streaming.resource_budgets.active_set;
  for (const key of ["asset_bytes", "triangles", "texture_bytes", "draw_calls"]) {
    assert(interactions.restored_ready_streaming.active_resource_metrics[key] <= activeBudget[`max_${key}`], `Declared ${key} active-set budget was exceeded`);
  }
  assert(interactions.restored_ready_streaming.transaction.elapsed_ms <= activeBudget.max_transaction_latency_ms, "Streaming transaction latency budget was exceeded");
  assert(interactions.renderer_metrics.triangles <= activeBudget.max_triangles && interactions.renderer_metrics.draw_calls <= activeBudget.max_draw_calls, "Measured renderer triangle/draw-call budget was exceeded");
  assert(state.eye_height_m === 1.68, "Human eye height drifted");
  assert(state.smaller_pyramid_count === 2, "Small Pyramid count diverged from official Louvre page");
  assert(state.collider_count >= 12 && state.route_count >= 5 && state.landmark_count >= 6, "Navigation evidence is incomplete");
  assert(state.bookmark_count >= 5 && state.truth_marker_count >= 5, "Owner-review bookmarks or in-world truth markers are incomplete");
  assert(state.route_checks.every((route) => route.status === "clear"), "A declared route is obstructed");
  assert(state.route_measurements.start.progress_percent === 0 && state.route_measurements.finish.progress_percent === 100, "Route progress endpoints are not measurable and reproducible");
  assert(state.route_measurements.start.total_length_m > 0 && state.route_measurements.start.remaining_route_m > 0, "Route length metrics are incomplete");
  assert(state.collision_probes.main_pyramid && state.collision_probes.west_pool && !state.collision_probes.clear_arrival, "Collision probes failed");
  assert(!state.movement_probes.blocked_move_accepted && state.movement_probes.safe_move_accepted, "Fail-closed movement probe failed");
  assert(state.route_selected && state.snapshot.active_route_id, "Review route could not be selected");
  assert(state.bookmark_probes.arrival_selected && state.bookmark_probes.entrance_selected && state.bookmark_probes.screenshot_selected, "A fixed review bookmark could not be selected");
  assert(JSON.stringify(state.bookmark_probes.arrival_snapshot.position_m) === JSON.stringify([0, 1.68, 62]), "Arrival bookmark position drifted");
  assert(JSON.stringify(state.bookmark_probes.entrance_snapshot.position_m) === JSON.stringify([0, 1.68, 34]), "Entrance bookmark position drifted");
  assert(state.snapshot.active_bookmark_id === "two_small_pyramids" && state.snapshot.truth_markers_visible, "Screenshot bookmark or truth markers are not reproducible");
  assert(state.snapshot.actor_manifest_requested === false && state.snapshot.tardis_present === false, "Actor or TARDIS was requested in solo mode");
  assert(state.truth_chip_count >= 3 && state.feedback_panel_present && state.bookmark_panel_present, "Truth, bookmark, or feedback UI is missing");
  assert(state.bookmark_option_count === state.bookmark_count && state.bookmark_link.includes("bookmark=two_small_pyramids"), "Bookmark selector/link is incomplete");
  assert(state.route_metric_text.includes("remaining") && state.collision_metric_text.includes("Collisions:"), "Measurable route/collision feedback is not visible");
  assert(feedbackState.entries.length === 1 && feedbackState.entries[0].active_route_id && feedbackState.entries[0].active_bookmark_id, "Feedback did not retain route/bookmark context");
  assert(feedbackState.entries[0].measurements.collision_events >= 1, "Feedback did not retain collision metrics");
  assert(packageState.package_kind === "louvre_solo_owner_review_package" && packageState.server_write_enabled === false, "Review package kind/read-only contract failed");
  assert(packageState.build_id === state.build_id && packageState.active_bookmark_id === "two_small_pyramids", "Review package is not bound to the active build/bookmark");
  assert(packageState.feedback_count === 1 && packageState.collision_events >= 1 && packageState.contract_bookmark_count === state.bookmark_count, "Review package omitted feedback, measurements, or bookmarks");
  assert(packageState.capture_bytes > 10000 && packageState.capture_sha256 === packageState.computed_capture_sha256, "Embedded PNG capture or SHA-256 is invalid");
  assert(bookmarkScreenshots.length === state.bookmark_count && bookmarkScreenshots.every((item) => item.bytes > 10000), "Fixed bookmark screenshot evidence is incomplete");
  assert(renderSample.canvas.width > 0 && renderSample.canvas.height > 0 && renderSample.frames > 0, "Three.js canvas did not render");
  assert(renderSample.unique_rgba_samples > 4 && renderSample.opaque_samples > 0, "Canvas lacks visible rendered variation");
  assert(screenshot.length > 10000 && entranceDoorScreenshot.length > 10000 && circulationScreenshot.length > 10000, "Exterior/entrance/circulation screenshots are unexpectedly empty");
  assert(truthPanel.length > 3000 && bookmarkPanel.length > 3000, "Review UI screenshots are unexpectedly empty");
  assert(diagnostics.page_errors.length === 0, `Page errors: ${diagnostics.page_errors.join(" | ")}`);
  assert(diagnostics.console_errors.length === 0, `Console errors: ${diagnostics.console_errors.join(" | ")}`);
  assert(diagnostics.request_failures.length === 0, `Request failures: ${diagnostics.request_failures.join(" | ")}`);
  assert(diagnostics.http_errors.length === 0, `HTTP errors: ${diagnostics.http_errors.join(" | ")}`);

  report = {
    ...report,
    status: "passed",
    state,
    feedback_state: { entry_count: feedbackState.entries.length, visible_status: feedbackState.status },
    package_state: packageState,
    bookmark_screenshots: bookmarkScreenshots,
    render_sample: renderSample,
    screenshot: {
      path: screenshotPath,
      bytes: screenshot.length,
      sha256: crypto.createHash("sha256").update(screenshot).digest("hex"),
    },
    approximate_entrance_screenshot: {
      path: entranceDoorPath,
      bytes: entranceDoorScreenshot.length,
      sha256: crypto.createHash("sha256").update(entranceDoorScreenshot).digest("hex"),
    },
    approximate_circulation_screenshot: {
      path: circulationPath,
      bytes: circulationScreenshot.length,
      sha256: crypto.createHash("sha256").update(circulationScreenshot).digest("hex"),
    },
    truth_panel_screenshot: {
      path: truthPanelPath,
      bytes: truthPanel.length,
      sha256: crypto.createHash("sha256").update(truthPanel).digest("hex"),
    },
    bookmark_panel_screenshot: {
      path: bookmarkPanelPath,
      bytes: bookmarkPanel.length,
      sha256: crypto.createHash("sha256").update(bookmarkPanel).digest("hex"),
    },
  };
} catch (error) {
  report.error = error instanceof Error ? error.stack || error.message : String(error);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: report.status, report: reportPath, error: report.error || null })}\n`);
}
