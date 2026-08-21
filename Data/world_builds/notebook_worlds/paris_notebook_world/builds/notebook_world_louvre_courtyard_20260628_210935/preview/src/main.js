import * as THREE from "three";
import { PointerLockControls } from "three/examples/jsm/controls/PointerLockControls.js";
import louvreContract from "../louvre_exterior_contract.json";
import louvreStreamingContract from "../louvre_cell_streaming_contract.json";
import { createLouvreCellStreamingScaffold } from "./louvre_cell_streaming.js";
import "./style.css";

const canvas = document.querySelector("#world");
const statusEl = document.querySelector("#status");
const params = new URLSearchParams(location.search);
const showActorsRequested = params.get("actors") === "1";
const photoModeDefault = params.get("photo") === "1";
const showSourceLabels = params.get("labels") === "1";
const showNameLabels = params.get("names") === "1";
const showReferenceDecals = params.get("refs") === "1";
const areaParam = params.get("area");
const requestedArea = ["tardis", "vosges"].includes(areaParam) ? areaParam : "louvre";
const soloLouvreMode = requestedArea === "louvre" && params.get("solo") !== "0";
const showActors = showActorsRequested && !soloLouvreMode;
const requestedView = params.get("view") || "";
const requestedBookmarkId = params.get("bookmark") || "arrival_scale";
const parisTardisArrived = !soloLouvreMode && (params.get("arrival") === "tardis" || params.get("tardis") === "arrived");
let currentArea = requestedArea;
let travelCooldown = 0;
const spawnedActors = [];
const avatarClearanceRadius = louvreContract.scale.avatar_clearance_radius_m;
const louvreCellStreaming = createLouvreCellStreamingScaffold(louvreStreamingContract);
const landmarkStatusEl = document.querySelector("#landmarkStatus");
let activeReviewRouteIndex = -1;
let activeReviewRouteLine = null;
let currentNearestLandmark = null;
let activeReviewBookmarkIndex = -1;
let truthMarkersVisible = true;
const truthMarkerMeshes = [];
const truthMarkerAnchors = [];
const collisionDebounceAt = new Map();
const reviewSessionMetrics = {
  started_at: new Date().toISOString(),
  distance_walked_m: 0,
  collision_events: 0,
  collision_by_id: {},
  last_collision_id: null,
  last_collision_message: null,
  last_collision_at: null,
};
const tardisNotebookWorlds = [
  {
    id: "home_world",
    title: "Home World",
    type: "main notebook world",
    status: "active",
    progress: "ready",
    source: "Kira & Lisa home anchor",
    shellLocation: "home",
    area: "home",
    travelReady: true,
    largeMap: false,
    areas: [
      { title: "Home", area: "home", shellLocation: "home", status: "active", progress: "ready", source: "home-world anchor", travelReady: true },
      { title: "Public Library", area: "library", shellLocation: "library", status: "nearby", progress: "first room", source: "local Data/library catalog", travelReady: true },
    ],
  },
  {
    id: "paris_notebook_world",
    title: "Paris Notebook World",
    type: "saved notebook world",
    status: "prototype needs realism rebuild",
    progress: "Louvre/Vosges seed maps",
    source: "Paris is a large notebook world; choose the area before travel",
    shellLocation: "louvre",
    area: "louvre",
    travelReady: true,
    largeMap: true,
    areas: [
      {
        title: "Louvre approximate Pyramid circulation review (draft)",
        area: "louvre",
        shellLocation: "louvre",
        status: "prototype owner review; not approved",
        progress: "Cour Napoleon plus bounded entrance/descent blockout",
        source: "photo-supported approximate door/spiral-stair interaction; exact/full interior, elevators, galleries, and artwork remain locked",
        travelReady: true,
        ownerReviewOnly: true,
        allowedCaller: "robert_avatar",
        soloQuery: { solo: "1", bookmark: "arrival_scale" },
        runtimeRegisteredAsComplete: false,
      },
      { title: "Place des Vosges Park", area: "vosges", shellLocation: "vosges", status: "seed", progress: "12%", source: "source-labeled park blueprint seed", travelReady: true },
    ],
  },
  {
    id: "new_notebook_world",
    title: "Create New Notebook World",
    type: "world builder request",
    status: "talk command needed",
    progress: "blank",
    source: "Say what to build; the World Builder will need sources and approval before travel",
    travelReady: false,
    largeMap: false,
    areas: [],
  },
  {
    id: "memory_reconstruction",
    title: "Memory Reconstruction",
    type: "memory world",
    status: "talk command needed",
    progress: "blank",
    source: "Say which memory to reconstruct; private details stay gated by the memory owner",
    travelReady: false,
    largeMap: false,
    areas: [],
  },
];

function flattenTardisDestinations() {
  return tardisNotebookWorlds.flatMap((world, worldIndex) => {
    const areas = world.areas?.length
      ? world.areas
      : [{ title: world.title, area: world.area || world.id, shellLocation: world.shellLocation, status: world.status, progress: world.progress, source: world.source, travelReady: world.travelReady }];
    return areas.map((area, areaIndex) => ({
      ...world,
      ...area,
      notebookId: world.id,
      notebookTitle: world.title,
      worldIndex,
      areaIndex,
      title: area.title || world.title,
      type: area.type || world.type,
      status: area.status || world.status,
      progress: area.progress || world.progress,
      source: area.source || world.source,
      travelReady: Boolean(area.travelReady ?? world.travelReady),
    }));
  });
}

const tardisDestinations = flattenTardisDestinations();
const tardisState = {
  inside: false,
  selectedDestination: 0,
  selectedNotebookWorld: 0,
  selectedNotebookArea: 0,
  previewedDestination: null,
  doorOpen: false,
  exteriorGroup: null,
  exteriorObjects: [],
  consoleScreen: null,
  frontDoorLeft: null,
  frontDoorRight: null,
  consolePreview: null,
};
const tardisCallerId = params.get("caller") || "robert_avatar";
let tardisConsolePanel = null;

const TARDIS_RETURN_LABELS = {
  home: "Home World",
  library: "Public Library",
  louvre: "Louvre Courtyard / Pyramid",
  vosges: "Place des Vosges",
};

function returnAreaLabel(area = safeReturnArea()) {
  return TARDIS_RETURN_LABELS[area] || area || "parked world";
}

function selectedTardisNotebookWorld() {
  return tardisNotebookWorlds[tardisState.selectedNotebookWorld] || tardisNotebookWorlds[0];
}

function syncTardisFlatSelection() {
  const index = tardisDestinations.findIndex((destination) =>
    destination.worldIndex === tardisState.selectedNotebookWorld &&
    destination.areaIndex === tardisState.selectedNotebookArea
  );
  tardisState.selectedDestination = index >= 0 ? index : 0;
}

function setTardisSelection(worldIndex, areaIndex = 0) {
  const safeWorld = THREE.MathUtils.clamp(Math.trunc(worldIndex), 0, tardisNotebookWorlds.length - 1);
  const world = tardisNotebookWorlds[safeWorld];
  const areaCount = Math.max(1, world.areas?.length || 1);
  tardisState.selectedNotebookWorld = safeWorld;
  tardisState.selectedNotebookArea = THREE.MathUtils.clamp(Math.trunc(areaIndex), 0, areaCount - 1);
  syncTardisFlatSelection();
}

function selectedTardisDestination() {
  return tardisDestinations[tardisState.selectedDestination % tardisDestinations.length];
}

function safeReturnArea() {
  const returnArea = params.get("return");
  return ["home", "library", "louvre", "vosges"].includes(returnArea) ? returnArea : "louvre";
}

function getTardisUseRecord() {
  try {
    const record = JSON.parse(localStorage.getItem("kira_tardis_active_use") || "null");
    if (!record?.user || Date.now() - Number(record.startedAt || 0) > 30 * 60 * 1000) {
      localStorage.removeItem("kira_tardis_active_use");
      return null;
    }
    return record;
  } catch {
    localStorage.removeItem("kira_tardis_active_use");
    return null;
  }
}

function requestTardisUse(user = tardisCallerId) {
  const active = getTardisUseRecord();
  if (active && active.user !== user) {
    const queue = JSON.parse(localStorage.getItem("kira_tardis_call_queue") || "[]");
    if (!queue.includes(user)) queue.push(user);
    localStorage.setItem("kira_tardis_call_queue", JSON.stringify(queue));
    statusEl.textContent = `The TARDIS is busy with ${active.user}. ${user} is waiting in the call queue.`;
    return false;
  }
  localStorage.setItem("kira_tardis_active_use", JSON.stringify({ user, startedAt: Date.now() }));
  return true;
}

function releaseTardisUse(user = tardisCallerId) {
  const active = getTardisUseRecord();
  if (!active || active.user === user) localStorage.removeItem("kira_tardis_active_use");
}

function requestShellLocation(location, options = {}) {
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ type: "kira-shell-location", location, ...options }, "*");
    return true;
  }
  statusEl.textContent = `The Kira World Shell is needed to travel to ${location}.`;
  return false;
}
document.body.classList.toggle("photo-mode", photoModeDefault);
if (requestedArea === "tardis") {
  document.title = "TARDIS Gateway Notebook Prototype";
  document.querySelector("#hud .title").textContent = "TARDIS Gateway Prototype";
  document.querySelector("#hud .meta").textContent = "Persistent bigger-inside travel hub - blueprint-first prototype";
  document.querySelector("#hud .controls").textContent = "Click to walk - WASD move - E exit door - world buttons or Talk command choose destinations - P snapshot";
} else if (requestedArea === "vosges") {
  document.title = "Place des Vosges Notebook Prototype";
  document.querySelector("#hud .title").textContent = "Place des Vosges Seed";
  document.querySelector("#hud .meta").textContent = "Paris Notebook World - blueprint-first park travel test";
  document.querySelector("#hud .controls").textContent = "Click to walk - WASD move - C call TARDIS - E enter when near - P snapshot";
} else if (soloLouvreMode) {
  document.title = "Louvre Bounded Circulation Solo Owner Review";
  document.querySelector("#hud .title").textContent = "Louvre Pyramid Circulation Owner Review";
  document.querySelector("#hud .meta").textContent = "Photo-supported approximate entrance/descent slice; exact/full interior, elevators, galleries, artwork, people, minds, voice, TARDIS, and Home World are not loaded";
  document.querySelector("#hud .controls").textContent = "Click scene - WASD - E operate approximate entrance - Shift faster - B bookmark - R route - F feedback - P snapshot - Esc release";
}

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xd8dde0);
scene.fog = new THREE.Fog(0xd8dde0, 190, 820);

const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.1, 900);
camera.position.set(0, louvreContract.scale.eye_height_m, photoModeDefault ? 66 : 62);

const controls = new PointerLockControls(camera, document.body);
canvas.addEventListener("click", () => controls.lock());
controls.addEventListener("lock", () => {
  statusEl.textContent = requestedArea === "tardis"
    ? `Walking mode active. Use a notebook-world button or Talk command, or exit back to ${returnAreaLabel()}.`
    : requestedArea === "vosges"
      ? "Walking mode active. C calls the TARDIS nearby, E enters it when you are at the doors."
      : soloLouvreMode
        ? "Solo owner review active. E operates the approximate entrance when its destination cells are collision-ready; B changes viewpoint, R changes route, and F opens feedback."
        : "Walking mode active. The pyramid glass blocks walking until the entrance is rebuilt from blueprint. C calls the TARDIS, P saves a snapshot.";
});
controls.addEventListener("unlock", () => {
  statusEl.textContent = "Paused. Click the scene to walk again.";
});
scene.add(controls.object);

const truthPanelEl = document.querySelector("#truthPanel");
const truthPanelBodyEl = document.querySelector("#truthPanelBody");
const truthToggleEl = document.querySelector("#truthToggle");
const feedbackToggleEl = document.querySelector("#feedbackToggle");
const feedbackPanelEl = document.querySelector("#feedbackPanel");
const feedbackCloseEl = document.querySelector("#feedbackClose");
const feedbackCategoryEl = document.querySelector("#feedbackCategory");
const feedbackVerdictEl = document.querySelector("#feedbackVerdict");
const feedbackNoteEl = document.querySelector("#feedbackNote");
const feedbackSaveEl = document.querySelector("#feedbackSave");
const feedbackExportEl = document.querySelector("#feedbackExport");
const feedbackStatusEl = document.querySelector("#feedbackStatus");
const reviewPackageExportEl = document.querySelector("#reviewPackageExport");
const packageStatusEl = document.querySelector("#packageStatus");
const bookmarkPanelEl = document.querySelector("#bookmarkPanel");
const bookmarkSelectEl = document.querySelector("#bookmarkSelect");
const bookmarkGoEl = document.querySelector("#bookmarkGo");
const bookmarkNextEl = document.querySelector("#bookmarkNext");
const bookmarkCopyEl = document.querySelector("#bookmarkCopy");
const bookmarkLinkEl = document.querySelector("#bookmarkLink");
const bookmarkStatusEl = document.querySelector("#bookmarkStatus");
const truthMarkersToggleEl = document.querySelector("#truthMarkersToggle");
const routeMetricEl = document.querySelector("#routeMetric");
const walkMetricEl = document.querySelector("#walkMetric");
const collisionMetricEl = document.querySelector("#collisionMetric");

function readReviewFeedback() {
  try {
    const value = JSON.parse(localStorage.getItem(louvreContract.feedback.storage_key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function updateFeedbackStatus(message = "") {
  if (!feedbackStatusEl) return;
  const count = readReviewFeedback().length;
  feedbackStatusEl.textContent = message || `${count} feedback entr${count === 1 ? "y" : "ies"} saved in this browser.`;
}

function setFeedbackOpen(open) {
  if (!soloLouvreMode || !feedbackPanelEl || !feedbackToggleEl) return;
  feedbackPanelEl.hidden = !open;
  feedbackToggleEl.setAttribute("aria-expanded", String(open));
  if (open) {
    controls.unlock();
    updateFeedbackStatus();
    feedbackNoteEl?.focus();
  }
}

function currentReviewBookmark() {
  return louvreContract.review_bookmarks[activeReviewBookmarkIndex] || null;
}

function reviewBookmarkUrl(bookmarkId) {
  const url = new URL(location.href);
  url.search = "";
  url.hash = "";
  url.searchParams.set("solo", "1");
  url.searchParams.set("bookmark", bookmarkId);
  return url.href;
}

function setReviewBookmark(reference, { updateUrl = true } = {}) {
  if (!soloLouvreMode || !louvreContract.review_bookmarks.length) return false;
  const index = typeof reference === "number"
    ? THREE.MathUtils.euclideanModulo(reference, louvreContract.review_bookmarks.length)
    : louvreContract.review_bookmarks.findIndex((bookmark) => bookmark.id === reference);
  if (index < 0) return false;
  activeReviewBookmarkIndex = index;
  const bookmark = louvreContract.review_bookmarks[index];
  controls.unlock();
  camera.position.set(...bookmark.position);
  louvreReviewRuntime.lastSurface = { floor_y_m: bookmark.position[1] - louvreContract.scale.eye_height_m, cell_id: "cour_napoleon_exterior", kind: "exterior" };
  void requestLouvreStreamingForPosition(camera.position, true);
  camera.lookAt(...bookmark.target);
  const routeIndex = louvreContract.routes.findIndex((route) => route.id === bookmark.route_id);
  if (routeIndex >= 0 && routeIndex !== activeReviewRouteIndex) setReviewRoute(routeIndex);
  if (bookmarkSelectEl) bookmarkSelectEl.value = bookmark.id;
  const bookmarkUrl = reviewBookmarkUrl(bookmark.id);
  if (bookmarkLinkEl) bookmarkLinkEl.value = bookmarkUrl;
  if (bookmarkStatusEl) {
    bookmarkStatusEl.textContent = `${index + 1}/${louvreContract.review_bookmarks.length}: ${bookmark.label} · ${bookmark.truth_scope.replaceAll("_", " ")} · route ${bookmark.route_id}`;
  }
  if (updateUrl) history.replaceState(null, "", bookmarkUrl);
  updateNearestLandmark();
  updateReviewMetricDisplay(true);
  statusEl.textContent = `Fixed review viewpoint ${index + 1}/${louvreContract.review_bookmarks.length}: ${bookmark.label}. Press B for the next reproducible view.`;
  return true;
}

function cycleReviewBookmark() {
  return setReviewBookmark(activeReviewBookmarkIndex + 1);
}

async function copyReviewBookmarkLink() {
  const bookmark = currentReviewBookmark() || louvreContract.review_bookmarks[0];
  const value = reviewBookmarkUrl(bookmark.id);
  if (bookmarkLinkEl) bookmarkLinkEl.value = value;
  try {
    await navigator.clipboard.writeText(value);
    if (bookmarkStatusEl) bookmarkStatusEl.textContent = `Copied reproducible link for “${bookmark.label}”.`;
    return true;
  } catch {
    bookmarkLinkEl?.focus();
    bookmarkLinkEl?.select();
    if (bookmarkStatusEl) bookmarkStatusEl.textContent = "Clipboard access was unavailable; the complete link is selected for manual copy.";
    return false;
  }
}

function setTruthMarkersVisible(visible) {
  truthMarkersVisible = Boolean(visible);
  for (const marker of truthMarkerMeshes) marker.visible = truthMarkersVisible;
  for (const anchor of truthMarkerAnchors) anchor.visible = truthMarkersVisible;
  if (truthMarkersToggleEl) {
    truthMarkersToggleEl.setAttribute("aria-pressed", String(truthMarkersVisible));
    truthMarkersToggleEl.textContent = truthMarkersVisible ? "Markers on" : "Markers off";
  }
  return truthMarkersVisible;
}

function setupReviewBookmarks() {
  if (!soloLouvreMode) {
    if (bookmarkPanelEl) bookmarkPanelEl.hidden = true;
    return;
  }
  if (bookmarkSelectEl) {
    bookmarkSelectEl.replaceChildren();
    for (const bookmark of louvreContract.review_bookmarks) {
      const option = document.createElement("option");
      option.value = bookmark.id;
      option.textContent = bookmark.label;
      bookmarkSelectEl.append(option);
    }
    bookmarkSelectEl.value = louvreContract.review_bookmarks.some((bookmark) => bookmark.id === requestedBookmarkId)
      ? requestedBookmarkId
      : louvreContract.review_bookmarks[0].id;
  }
  bookmarkGoEl?.addEventListener("click", () => setReviewBookmark(bookmarkSelectEl?.value || 0));
  bookmarkNextEl?.addEventListener("click", cycleReviewBookmark);
  bookmarkCopyEl?.addEventListener("click", copyReviewBookmarkLink);
  truthMarkersToggleEl?.addEventListener("click", () => setTruthMarkersVisible(!truthMarkersVisible));
}

function saveReviewFeedback() {
  const note = feedbackNoteEl?.value.trim() || "";
  if (!note) {
    updateFeedbackStatus("Please describe what worked or what needs improvement before saving.");
    feedbackNoteEl?.focus();
    return false;
  }
  const position = controls.object.position;
  const route = louvreContract.routes[activeReviewRouteIndex] || null;
  const bookmark = currentReviewBookmark();
  const entries = readReviewFeedback();
  entries.push({
    schema_version: 1,
    created_at: new Date().toISOString(),
    build_id: louvreContract.build_id,
    category: feedbackCategoryEl?.value || "other",
    verdict: feedbackVerdictEl?.value || "not_tested",
    note,
    viewer_position_m: {
      x: Number(position.x.toFixed(3)),
      y: Number(position.y.toFixed(3)),
      z: Number(position.z.toFixed(3)),
      yaw_radians: Number(camera.rotation.y.toFixed(4)),
    },
    nearest_landmark_id: currentNearestLandmark?.id || null,
    active_route_id: route?.id || null,
    active_bookmark_id: bookmark?.id || null,
    reproducible_bookmark_url: bookmark ? reviewBookmarkUrl(bookmark.id) : null,
    measurements: reviewMetricsSnapshot(),
    truth_scope: "official_dimensions_with_approximate_exterior_geometry",
  });
  localStorage.setItem(louvreContract.feedback.storage_key, JSON.stringify(entries));
  feedbackNoteEl.value = "";
  updateFeedbackStatus(`Saved entry ${entries.length} locally. Export JSON when you want to share it.`);
  return true;
}

function exportReviewFeedback() {
  const entries = readReviewFeedback();
  const payload = {
    schema_version: 1,
    world_id: louvreContract.world_id,
    location_id: louvreContract.location_id,
    build_id: louvreContract.build_id,
    exported_at: new Date().toISOString(),
    source_truth_status: louvreContract.status,
    entry_count: entries.length,
    entries,
  };
  downloadJson(
    payload,
    `louvre_solo_review_feedback_${new Date().toISOString().replace(/[:.]/g, "-")}.json`,
  );
  updateFeedbackStatus(`Exported ${entries.length} local feedback entr${entries.length === 1 ? "y" : "ies"}.`);
}

function downloadJson(payload, filename) {
  const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(href), 0);
}

function dataUrlBytes(dataUrl) {
  const encoded = dataUrl.slice(dataUrl.indexOf(",") + 1);
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index++) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

async function sha256Hex(bytes) {
  if (!globalThis.crypto?.subtle) return null;
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

async function buildOwnerReviewPackage({ includeCapture = true } = {}) {
  const createdAt = new Date().toISOString();
  const bookmark = currentReviewBookmark();
  const route = louvreContract.routes[activeReviewRouteIndex] || null;
  renderer.render(scene, camera);
  let capture = null;
  if (includeCapture) {
    const dataUrl = renderer.domElement.toDataURL("image/png");
    const bytes = dataUrlBytes(dataUrl);
    capture = {
      mime_type: "image/png",
      encoding: "data_url",
      width_px: renderer.domElement.width,
      height_px: renderer.domElement.height,
      bytes: bytes.byteLength,
      sha256: await sha256Hex(bytes),
      data_url: dataUrl,
    };
  }
  return {
    schema_version: louvreContract.review_package.schema_version,
    package_kind: louvreContract.review_package.kind,
    created_at: createdAt,
    world_id: louvreContract.world_id,
    location_id: louvreContract.location_id,
    build_id: louvreContract.build_id,
    status: louvreContract.status,
    server_write_enabled: false,
    source_and_isolation_contract: louvreContract,
    reproducible_review: {
      active_bookmark_id: bookmark?.id || null,
      active_bookmark_label: bookmark?.label || null,
      url: bookmark ? reviewBookmarkUrl(bookmark.id) : null,
      camera_position_m: camera.position.toArray().map((value) => Number(value.toFixed(4))),
      camera_quaternion: camera.quaternion.toArray().map((value) => Number(value.toFixed(6))),
      nearest_landmark_id: currentNearestLandmark?.id || null,
      active_route_id: route?.id || null,
    },
    route_checks: runStaticRouteChecks(),
    measurements: reviewMetricsSnapshot(),
    feedback_entries: readReviewFeedback(),
    capture,
  };
}

async function exportOwnerReviewPackage() {
  if (!soloLouvreMode || !reviewPackageExportEl) return false;
  reviewPackageExportEl.disabled = true;
  if (packageStatusEl) packageStatusEl.textContent = "Building the local review package and PNG capture…";
  try {
    const payload = await buildOwnerReviewPackage({ includeCapture: true });
    const bookmarkId = payload.reproducible_review.active_bookmark_id || "unbookmarked";
    const stamp = payload.created_at.replace(/[:.]/g, "-");
    downloadJson(payload, `louvre_owner_review_${bookmarkId}_${stamp}.json`);
    if (packageStatusEl) {
      packageStatusEl.textContent = `Exported a self-contained local package (${payload.capture.bytes.toLocaleString()} PNG bytes, SHA-256 ${payload.capture.sha256 || "unavailable"}).`;
    }
    return true;
  } catch (error) {
    if (packageStatusEl) packageStatusEl.textContent = `Package export failed locally: ${error instanceof Error ? error.message : String(error)}`;
    return false;
  } finally {
    reviewPackageExportEl.disabled = false;
  }
}

function setupLouvreReviewUi() {
  if (!soloLouvreMode) {
    if (truthPanelEl) truthPanelEl.hidden = true;
    if (feedbackToggleEl) feedbackToggleEl.hidden = true;
    if (feedbackPanelEl) feedbackPanelEl.hidden = true;
    if (bookmarkPanelEl) bookmarkPanelEl.hidden = true;
    return;
  }
  truthToggleEl?.addEventListener("click", () => {
    const expanded = truthToggleEl.getAttribute("aria-expanded") !== "false";
    truthToggleEl.setAttribute("aria-expanded", String(!expanded));
    truthToggleEl.textContent = expanded ? "Show" : "Hide";
    if (truthPanelBodyEl) truthPanelBodyEl.hidden = expanded;
  });
  feedbackToggleEl?.addEventListener("click", () => setFeedbackOpen(feedbackPanelEl.hidden));
  feedbackCloseEl?.addEventListener("click", () => setFeedbackOpen(false));
  feedbackSaveEl?.addEventListener("click", saveReviewFeedback);
  feedbackExportEl?.addEventListener("click", exportReviewFeedback);
  reviewPackageExportEl?.addEventListener("click", exportOwnerReviewPackage);
  setupReviewBookmarks();
  updateFeedbackStatus();
}

setupLouvreReviewUi();

scene.add(new THREE.HemisphereLight(0xdcecff, 0x4f4639, 2.0));
const sun = new THREE.DirectionalLight(0xfff2d3, 4.2);
sun.position.set(-80, 120, 50);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -180;
sun.shadow.camera.right = 180;
sun.shadow.camera.top = 180;
sun.shadow.camera.bottom = -180;
scene.add(sun);

function makeSkyMaterial() {
  const skyCanvas = document.createElement("canvas");
  skyCanvas.width = 1024;
  skyCanvas.height = 512;
  const ctx = skyCanvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, skyCanvas.height);
  gradient.addColorStop(0, "#78add9");
  gradient.addColorStop(0.55, "#c7ddea");
  gradient.addColorStop(1, "#eef1e7");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, skyCanvas.width, skyCanvas.height);
  ctx.fillStyle = "rgba(255,255,255,0.72)";
  for (const cloud of [
    [160, 120, 70, 22], [220, 110, 88, 28], [300, 126, 72, 22],
    [650, 85, 95, 26], [735, 96, 120, 34], [820, 82, 70, 24],
    [430, 180, 70, 18], [500, 170, 96, 24], [570, 182, 65, 18],
  ]) {
    ctx.beginPath();
    ctx.ellipse(cloud[0], cloud[1], cloud[2], cloud[3], 0, 0, Math.PI * 2);
    ctx.fill();
  }
  const texture = new THREE.CanvasTexture(skyCanvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return new THREE.MeshBasicMaterial({ map: texture, side: THREE.BackSide });
}

const skyDome = new THREE.Mesh(new THREE.SphereGeometry(430, 48, 24), makeSkyMaterial());
skyDome.name = "review sky dome with procedural clouds";
skyDome.position.y = 12;
skyDome.visible = false;
scene.add(skyDome);

const materials = {
  stone: new THREE.MeshStandardMaterial({ color: 0xd4c6a7, roughness: 0.9 }),
  stoneDark: new THREE.MeshStandardMaterial({ color: 0xa89473, roughness: 0.94 }),
  glass: new THREE.MeshPhysicalMaterial({
    color: 0xc5d7d8,
    transparent: true,
    opacity: 0.28,
    roughness: 0.025,
    metalness: 0.02,
    transmission: 0.55,
  }),
  metal: new THREE.MeshStandardMaterial({ color: 0x4b5860, roughness: 0.35, metalness: 0.45 }),
  darkMetal: new THREE.LineBasicMaterial({ color: 0x26343a, transparent: true, opacity: 0.86 }),
  water: new THREE.MeshPhysicalMaterial({ color: 0x5d90a6, transparent: true, opacity: 0.58, roughness: 0.08 }),
  pavingA: new THREE.MeshStandardMaterial({ color: 0xb7aa92, roughness: 0.95 }),
  pavingB: new THREE.MeshStandardMaterial({ color: 0xa69a85, roughness: 0.95 }),
  pavingCool: new THREE.MeshStandardMaterial({ color: 0x9ca5a6, roughness: 0.94 }),
  cobble: new THREE.MeshStandardMaterial({ color: 0xb8b7b0, roughness: 0.96 }),
  creamWall: new THREE.MeshStandardMaterial({ color: 0xe7e0cf, roughness: 0.88 }),
  pastryWarm: new THREE.MeshStandardMaterial({ color: 0xe9b16d, roughness: 0.72 }),
  leaf: new THREE.MeshStandardMaterial({ color: 0x4f8f55, roughness: 0.8 }),
  rope: new THREE.MeshStandardMaterial({ color: 0xd4d0c2, roughness: 0.42, metalness: 0.15 }),
  sign: new THREE.MeshStandardMaterial({ color: 0x1e252b, roughness: 0.55 }),
  label: new THREE.MeshBasicMaterial({ color: 0xffffff }),
};

const textureLoader = new THREE.TextureLoader();

function makePatternTexture(kind, base, line, accent) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext("2d");
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.globalAlpha = 0.22;
  for (let i = 0; i < 1800; i++) {
    const v = 160 + Math.floor(Math.random() * 80);
    ctx.fillStyle = `rgb(${v},${v - 8},${v - 22})`;
    ctx.fillRect(Math.random() * c.width, Math.random() * c.height, 1 + Math.random() * 2, 1 + Math.random() * 2);
  }
  ctx.globalAlpha = 1;
  ctx.strokeStyle = line;
  ctx.lineWidth = kind === "paving" ? 2 : 1.4;
  if (kind === "paving") {
    for (let x = 0; x <= c.width; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x + 26, c.height);
      ctx.stroke();
    }
    for (let y = 0; y <= c.height; y += 64) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(c.width, y + 18);
      ctx.stroke();
    }
  } else {
    for (let y = 34; y < c.height; y += 48) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(c.width, y + (y % 96 === 0 ? 6 : -4));
      ctx.stroke();
    }
    ctx.strokeStyle = accent;
    for (let x = 0; x < c.width; x += 96) {
      ctx.beginPath();
      ctx.moveTo(x + 8, 0);
      ctx.lineTo(x - 12, c.height);
      ctx.stroke();
    }
  }
  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(kind === "paving" ? 18 : 5, kind === "paving" ? 14 : 4);
  return texture;
}

materials.stone.map = makePatternTexture("stone", "#d8caaa", "rgba(95,80,55,0.25)", "rgba(255,245,215,0.13)");
materials.stone.needsUpdate = true;
materials.pavingA.map = makePatternTexture("paving", "#d1c3a6", "rgba(105,95,72,0.32)", "rgba(255,245,215,0.12)");
materials.pavingA.needsUpdate = true;
materials.pavingCool.map = makePatternTexture("paving", "#b5b9b4", "rgba(88,96,93,0.3)", "rgba(255,255,255,0.1)");
materials.pavingCool.needsUpdate = true;

function addBox(name, size, position, material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(size.x, size.y, size.z), material);
  mesh.name = name;
  mesh.position.copy(position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

function addBoxYaw(name, size, position, material, rotationY) {
  const mesh = addBox(name, size, position, material);
  mesh.rotation.y = rotationY;
  return mesh;
}

function addPlane(name, width, depth, position, material) {
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, depth), material);
  mesh.name = name;
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.copy(position);
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

function addGroundAroundRect(name, outer, opening, y, material) {
  const [outerMinX, outerMaxX, outerMinZ, outerMaxZ] = outer;
  const [holeMinX, holeMaxX, holeMinZ, holeMaxZ] = opening;
  const pieces = [
    [outerMinX, outerMaxX, outerMinZ, holeMinZ, "north"],
    [outerMinX, outerMaxX, holeMaxZ, outerMaxZ, "south"],
    [outerMinX, holeMinX, holeMinZ, holeMaxZ, "west"],
    [holeMaxX, outerMaxX, holeMinZ, holeMaxZ, "east"],
  ];
  return pieces.flatMap(([minX, maxX, minZ, maxZ, suffix]) => {
    const width = maxX - minX;
    const depth = maxZ - minZ;
    if (width <= 0 || depth <= 0) return [];
    return [addPlane(`${name} ${suffix}`, width, depth, new THREE.Vector3((minX + maxX) / 2, y, (minZ + maxZ) / 2), material)];
  });
}

function addImagePlane(name, src, width, height, position, rotationY = 0) {
  const texture = textureLoader.load(src);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
  mesh.name = name;
  mesh.position.copy(position);
  mesh.rotation.y = rotationY;
  mesh.visible = showReferenceDecals;
  mesh.renderOrder = 6;
  scene.add(mesh);
  return mesh;
}

function makeLabel(text, width = 3.4, height = 1.0, fontSize = 42, theme = {}) {
  const canvas2d = document.createElement("canvas");
  canvas2d.width = 2048;
  canvas2d.height = Math.max(384, Math.round(2048 * height / width));
  const ctx = canvas2d.getContext("2d");
  ctx.fillStyle = theme.background || "rgba(20, 24, 29, 0.86)";
  ctx.fillRect(0, 0, canvas2d.width, canvas2d.height);
  ctx.strokeStyle = theme.border || "rgba(255,255,255,0.42)";
  ctx.lineWidth = 6;
  ctx.strokeRect(3, 3, canvas2d.width - 6, canvas2d.height - 6);
  ctx.fillStyle = theme.text || "#f5efe2";
  ctx.font = `700 ${fontSize}px Arial`;
  const words = text.split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > canvas2d.width - 144 && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  let y = fontSize * 1.35;
  for (const item of lines.slice(0, 6)) {
    ctx.fillText(item, 72, y);
    y += fontSize * 1.28;
  }
  const texture = new THREE.CanvasTexture(canvas2d);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
  return mesh;
}

function makeSignText(text, width = 3.8, height = 0.28, fontSize = 70) {
  const canvas2d = document.createElement("canvas");
  canvas2d.width = 2048;
  canvas2d.height = Math.max(256, Math.round(2048 * height / width));
  const ctx = canvas2d.getContext("2d");
  ctx.clearRect(0, 0, canvas2d.width, canvas2d.height);
  ctx.fillStyle = "#f1eee5";
  ctx.font = `700 ${fontSize}px Arial`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas2d.width / 2, canvas2d.height / 2);
  const texture = new THREE.CanvasTexture(canvas2d);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide, depthTest: false });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
  mesh.renderOrder = 20;
  return mesh;
}

function placeSignText(text, position, rotationY = 0, width = 3.8, height = 0.28, fontSize = 70) {
  const label = makeSignText(text, width, height, fontSize);
  label.position.copy(position);
  label.rotation.y = rotationY;
  label.userData.isLabel = false;
  scene.add(label);
  return label;
}

function placeLabel(text, position, rotationY = 0, width = 6.6, height = 1.55, fontSize = 42, options = {}) {
  const label = makeLabel(text, width, height, fontSize);
  label.position.copy(position);
  label.rotation.y = rotationY;
  label.visible = Boolean(options.alwaysVisible || (options.actorName ? showNameLabels : showSourceLabels));
  label.userData.isLabel = !options.fixed;
  label.userData.actorName = Boolean(options.actorName);
  scene.add(label);
  return label;
}

function truthMarkerTheme(truth) {
  if (truth === "locked") {
    return { background: "rgba(78, 24, 28, 0.94)", border: "rgba(255, 154, 154, 0.96)", text: "#ffe5e5" };
  }
  if (truth === "approximate") {
    return { background: "rgba(86, 57, 16, 0.94)", border: "rgba(255, 202, 102, 0.96)", text: "#fff1ca" };
  }
  if (truth === "mixed") {
    return { background: "rgba(18, 57, 78, 0.94)", border: "rgba(119, 213, 246, 0.96)", text: "#e4f8ff" };
  }
  return { background: "rgba(17, 74, 52, 0.94)", border: "rgba(116, 235, 174, 0.96)", text: "#e1ffef" };
}

function truthMarkerColor(truth) {
  if (truth === "locked") return 0xf29a9a;
  if (truth === "approximate") return 0xffca66;
  if (truth === "mixed") return 0x77d5f6;
  return 0x74ebae;
}

function placeTruthMarker(marker) {
  const truth = marker.truth.startsWith("mixed_") ? "mixed" : marker.truth;
  const label = makeLabel(marker.label, 10.5, 1.65, 64, truthMarkerTheme(truth));
  label.name = `truth marker:${marker.id}`;
  label.position.set(...marker.position);
  label.visible = soloLouvreMode && truthMarkersVisible;
  label.userData.isLabel = true;
  label.userData.truthMarker = true;
  label.userData.truthMarkerId = marker.id;
  label.renderOrder = 8;
  scene.add(label);
  truthMarkerMeshes.push(label);
  const anchor = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(marker.position[0], 0.25, marker.position[2]),
      new THREE.Vector3(marker.position[0], marker.position[1] - 0.85, marker.position[2]),
    ]),
    new THREE.LineBasicMaterial({ color: truthMarkerColor(truth), transparent: true, opacity: 0.88 }),
  );
  anchor.name = `truth marker anchor:${marker.id}`;
  anchor.visible = soloLouvreMode && truthMarkersVisible;
  scene.add(anchor);
  truthMarkerAnchors.push(anchor);
  return label;
}

function makeColor(value, fallback) {
  try {
    return new THREE.Color(value || fallback);
  } catch {
    return new THREE.Color(fallback);
  }
}

function addCylinder(name, radius, height, position, material, radialSegments = 20) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, radialSegments), material);
  mesh.name = name;
  mesh.position.copy(position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

function addSphere(name, radius, position, material, widthSegments = 12, heightSegments = 8) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, widthSegments, heightSegments), material);
  mesh.name = name;
  mesh.position.copy(position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

function seededRandom(seed) {
  let value = seed >>> 0;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

function createGrassBladeGeometry() {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array([
    -0.018, 0, 0,
    0.018, 0, 0,
    -0.013, 0.085, 0.008,
    0.013, 0.085, 0.008,
    0, 0.19, 0.035,
  ]);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setIndex([0, 1, 2, 1, 3, 2, 2, 3, 4]);
  geometry.computeVertexNormals();
  return geometry;
}

function isInsideAvoidArea(x, z, area) {
  let dx = x - area.x;
  let dz = z - area.z;
  if (area.yaw) {
    const c = Math.cos(-area.yaw);
    const s = Math.sin(-area.yaw);
    const rx = dx * c - dz * s;
    const rz = dx * s + dz * c;
    dx = rx;
    dz = rz;
  }
  return Math.abs(dx) < area.sx / 2 && Math.abs(dz) < area.sz / 2;
}

function addGrassBladeField({ name, x, z, width, depth, count, y = 0.075, seed = 1, avoid = [] }) {
  const geometry = createGrassBladeGeometry();
  const material = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.96,
    side: THREE.DoubleSide,
    vertexColors: true,
  });
  const mesh = new THREE.InstancedMesh(geometry, material, count);
  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.frustumCulled = false;

  const rand = seededRandom(seed);
  const dummy = new THREE.Object3D();
  const color = new THREE.Color();
  let placed = 0;
  let attempts = 0;
  while (placed < count && attempts < count * 10) {
    attempts += 1;
    const px = x + (rand() - 0.5) * width;
    const pz = z + (rand() - 0.5) * depth;
    if (avoid.some((area) => isInsideAvoidArea(px, pz, area))) continue;
    dummy.position.set(px, y, pz);
    dummy.rotation.set((rand() - 0.5) * 0.22, rand() * Math.PI * 2, (rand() - 0.5) * 0.18);
    const bladeScale = 0.78 + rand() * 1.2;
    dummy.scale.set(0.75 + rand() * 0.85, bladeScale, 0.75 + rand() * 0.85);
    dummy.updateMatrix();
    mesh.setMatrixAt(placed, dummy.matrix);
    color.setHSL(0.24 + rand() * 0.08, 0.42 + rand() * 0.2, 0.27 + rand() * 0.2);
    mesh.setColorAt(placed, color);
    placed += 1;
  }
  mesh.count = placed;
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  scene.add(mesh);
  return mesh;
}

function addTorus(name, radius, tube, position, material, rotation = new THREE.Euler(), radialSegments = 12, tubularSegments = 32) {
  const mesh = new THREE.Mesh(new THREE.TorusGeometry(radius, tube, radialSegments, tubularSegments), material);
  mesh.name = name;
  mesh.position.copy(position);
  mesh.rotation.copy(rotation);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

function addReflectingPoolBasin(name, width, depth, x, z) {
  const curb = new THREE.MeshStandardMaterial({ color: 0xa99f8c, roughness: 0.88 });
  addBox(`${name} shallow basin`, new THREE.Vector3(width, 0.12, depth), new THREE.Vector3(x, 0.02, z), materials.stoneDark);
  addPlane(`${name} water`, width - 0.48, depth - 0.48, new THREE.Vector3(x, 0.095, z), materials.water);
  addBox(`${name} north curb`, new THREE.Vector3(width, 0.22, 0.24), new THREE.Vector3(x, 0.11, z - depth / 2), curb);
  addBox(`${name} south curb`, new THREE.Vector3(width, 0.22, 0.24), new THREE.Vector3(x, 0.11, z + depth / 2), curb);
  addBox(`${name} west curb`, new THREE.Vector3(0.24, 0.22, depth), new THREE.Vector3(x - width / 2, 0.11, z), curb);
  addBox(`${name} east curb`, new THREE.Vector3(0.24, 0.22, depth), new THREE.Vector3(x + width / 2, 0.11, z), curb);
}

function addStanchionLine(startX, endX, z, count) {
  const group = new THREE.Group();
  group.name = "queue stanchion line placeholder";
  scene.add(group);
  const metal = new THREE.MeshStandardMaterial({ color: 0x858a8b, roughness: 0.38, metalness: 0.6 });
  const rope = materials.rope;
  const previous = [];
  for (let i = 0; i < count; i++) {
    const t = count === 1 ? 0 : i / (count - 1);
    const x = THREE.MathUtils.lerp(startX, endX, t);
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.07, 1.05, 12), metal);
    post.position.set(x, 0.525, z);
    post.castShadow = true;
    group.add(post);
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 8), metal);
    cap.position.set(x, 1.08, z);
    cap.castShadow = true;
    group.add(cap);
    previous.push(new THREE.Vector3(x, 0.95, z));
  }
  for (let i = 0; i < previous.length - 1; i++) {
    const a = previous[i];
    const b = previous[i + 1];
    const mid = a.clone().lerp(b, 0.5);
    const length = a.distanceTo(b);
    const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, length, 8), rope);
    rail.position.copy(mid);
    rail.rotation.z = Math.PI / 2;
    rail.castShadow = true;
    group.add(rail);
    const curve = new THREE.CatmullRomCurve3([
      a.clone(),
      mid.clone().add(new THREE.Vector3(0, -0.18, 0)),
      b.clone(),
    ]);
    const ropeGeo = new THREE.TubeGeometry(curve, 12, 0.018, 8, false);
    const sag = new THREE.Mesh(ropeGeo, rope);
    sag.name = "sagging queue rope";
    sag.castShadow = true;
    group.add(sag);
  }
  return group;
}

function addStanchionLineZ(x, startZ, endZ, count) {
  const group = new THREE.Group();
  group.name = "approximate queue lane boundary";
  scene.add(group);
  const metal = new THREE.MeshStandardMaterial({ color: 0x858a8b, roughness: 0.38, metalness: 0.6 });
  const previous = [];
  for (let i = 0; i < count; i++) {
    const t = count === 1 ? 0 : i / (count - 1);
    const z = THREE.MathUtils.lerp(startZ, endZ, t);
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.07, 1.05, 12), metal);
    post.position.set(x, 0.525, z);
    post.castShadow = true;
    group.add(post);
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 8), metal);
    cap.position.set(x, 1.08, z);
    cap.castShadow = true;
    group.add(cap);
    previous.push(new THREE.Vector3(x, 0.95, z));
  }
  for (let i = 0; i < previous.length - 1; i++) {
    const a = previous[i];
    const b = previous[i + 1];
    const mid = a.clone().lerp(b, 0.5);
    const curve = new THREE.CatmullRomCurve3([a.clone(), mid.clone().add(new THREE.Vector3(0, -0.18, 0)), b.clone()]);
    const rope = new THREE.Mesh(new THREE.TubeGeometry(curve, 12, 0.024, 8, false), materials.rope);
    rope.name = "sagging approximate queue rope";
    rope.castShadow = true;
    group.add(rope);
  }
  return group;
}

function addVisitor(actor) {
  const spawn = actor.spawn || {};
  const appearance = actor.appearance || {};
  const root = new THREE.Group();
  root.name = `actor:${actor.actor_id}`;
  root.position.set(spawn.x || 0, spawn.y || 0, spawn.z || 0);
  root.rotation.y = THREE.MathUtils.degToRad(spawn.heading_degrees || 0);
  scene.add(root);

  const skin = new THREE.MeshStandardMaterial({ color: 0xd4a27f, roughness: 0.72 });
  const jacket = new THREE.MeshStandardMaterial({ color: makeColor(appearance.jacket, "#34465a"), roughness: 0.78 });
  const shirt = new THREE.MeshStandardMaterial({ color: makeColor(appearance.shirt, "#e8e8df"), roughness: 0.82 });
  const pants = new THREE.MeshStandardMaterial({ color: makeColor(appearance.pants, "#252932"), roughness: 0.82 });
  const hair = new THREE.MeshStandardMaterial({ color: actor.actor_id.includes("ladybug") ? 0x172a46 : 0x3a2a22, roughness: 0.9 });

  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.34, 0.95, 8, 16), jacket);
  body.position.y = 1.18;
  body.castShadow = true;
  root.add(body);
  const torsoFront = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.72, 0.055), shirt);
  torsoFront.position.set(0, 1.18, 0.31);
  torsoFront.castShadow = true;
  root.add(torsoFront);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.23, 18, 12), skin);
  head.position.y = 1.88;
  head.castShadow = true;
  root.add(head);
  const hairCap = new THREE.Mesh(new THREE.SphereGeometry(0.245, 18, 8, 0, Math.PI * 2, 0, Math.PI * 0.58), hair);
  hairCap.position.y = 1.95;
  hairCap.castShadow = true;
  root.add(hairCap);
  for (const x of [-0.18, 0.18]) {
    const leg = new THREE.Mesh(new THREE.CapsuleGeometry(0.105, 0.82, 6, 10), pants);
    leg.position.set(x, 0.46, 0);
    leg.castShadow = true;
    root.add(leg);
    const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.07, 0.74, 6, 10), skin);
    arm.position.set(x > 0 ? 0.45 : -0.45, 1.15, 0);
    arm.rotation.z = x > 0 ? -0.14 : 0.14;
    arm.castShadow = true;
    root.add(arm);
  }
  if (actor.display_name) {
    placeLabel(actor.display_name, root.position.clone().add(new THREE.Vector3(0, 2.55, 0)), 0, 3.3, 0.72, 50, { actorName: true });
    spawnedActors.push(root);
  }
  return root;
}

async function loadActorManifest() {
  if (!showActors) return;
  try {
    const response = await fetch("./actor_manifest.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`actor manifest returned ${response.status}`);
    const manifest = await response.json();
    for (const actor of manifest.actors || []) {
      const areaSpawn = actor.spawn_by_area?.[requestedArea];
      addVisitor(areaSpawn ? { ...actor, spawn: areaSpawn } : actor);
    }
    if (photoModeDefault) {
      if (requestedArea === "interior") {
        camera.position.set(-18, -8.8, 19);
        camera.lookAt(0, -4.2, 2);
      } else {
        camera.position.set(0, 4.2, 66);
        camera.lookAt(0, 7.0, 3);
      }
      statusEl.textContent = "Photo mode: visitor placeholders are visible because ?actors=1 is enabled.";
    }
  } catch (error) {
    console.warn("Actor manifest could not be loaded.", error);
  }
}

// Cour Napoleon prototype ground.  The main Pyramid footprint is intentionally
// left open so the separately streamed under-Pyramid review slice is not hidden
// behind an eager courtyard plane.
addGroundAroundRect(
  "Courtyard placeholder paving around Pyramid opening",
  [-115, 115, -90, 90],
  [-17.5, 17.5, -17.5, 17.5],
  0,
  materials.pavingA,
);
// The paving seams are texture-only for now. Thin mesh seam strips caused visible z-fighting/flicker while walking.
addGroundAroundRect(
  "cool grey visitor plaza paving around Pyramid opening",
  [-45, 45, -2, 50],
  [-17.5, 17.5, -2, 17.5],
  0.035,
  materials.pavingCool,
);

// Palace facade placeholders: massing only, not a final elevation.
addBox("North palace facade placeholder", new THREE.Vector3(210, 22, 7), new THREE.Vector3(0, 11, -83), materials.stone);
addBox("West palace wing placeholder", new THREE.Vector3(7, 20, 125), new THREE.Vector3(-108, 10, -16), materials.stone);
addBox("East palace wing placeholder", new THREE.Vector3(7, 20, 125), new THREE.Vector3(108, 10, -16), materials.stone);
addBox("left pavilion massing placeholder", new THREE.Vector3(28, 34, 11), new THREE.Vector3(-78, 17, -78), materials.stone);
addBox("right pavilion massing placeholder", new THREE.Vector3(28, 30, 11), new THREE.Vector3(72, 15, -78), materials.stone);
addBox("left dark mansard roof placeholder", new THREE.Vector3(30, 8, 13), new THREE.Vector3(-78, 36, -78), new THREE.MeshStandardMaterial({ color: 0x273141, roughness: 0.65 }));
addBox("right dark mansard roof placeholder", new THREE.Vector3(30, 7, 13), new THREE.Vector3(72, 32.5, -78), new THREE.MeshStandardMaterial({ color: 0x273141, roughness: 0.65 }));
for (const [x, y] of [[-92, 38], [-64, 38], [58, 34], [86, 34]]) {
  addBox("pavilion chimney/tower placeholder", new THREE.Vector3(2.2, 8, 2.2), new THREE.Vector3(x, y, -78), materials.stoneDark);
}

for (const pavilion of [
  { x: -78, bodyHeight: 34, roofY: 36 },
  { x: 72, bodyHeight: 30, roofY: 32.5 },
]) {
  const frontZ = -72.35;
  const x0 = pavilion.x;
  addBox("pavilion lower cornice placeholder", new THREE.Vector3(30, 0.55, 0.7), new THREE.Vector3(x0, 7.1, frontZ), materials.stoneDark);
  addBox("pavilion upper cornice placeholder", new THREE.Vector3(30, 0.7, 0.7), new THREE.Vector3(x0, pavilion.bodyHeight - 2.5, frontZ), materials.stoneDark);
  addBox("pavilion roof edge placeholder", new THREE.Vector3(31, 0.75, 0.8), new THREE.Vector3(x0, pavilion.roofY - 3.5, frontZ), materials.stoneDark);
  addBox("pavilion central arcade shadow placeholder", new THREE.Vector3(6.0, 6.4, 0.35), new THREE.Vector3(x0, 3.5, frontZ + 0.08), materials.stoneDark);
  for (const dx of [-10, -5, 5, 10]) {
    addBox("pavilion ground arch shadow placeholder", new THREE.Vector3(3.3, 5.5, 0.3), new THREE.Vector3(x0 + dx, 3.05, frontZ + 0.1), materials.stoneDark);
    addBox("pavilion column placeholder", new THREE.Vector3(0.45, 6.1, 0.55), new THREE.Vector3(x0 + dx - 2.0, 3.15, frontZ + 0.2), materials.stone);
    addBox("pavilion tall window shadow placeholder", new THREE.Vector3(2.3, 4.8, 0.28), new THREE.Vector3(x0 + dx, 13.6, frontZ + 0.1), materials.stoneDark);
    addBox("pavilion upper window shadow placeholder", new THREE.Vector3(2.1, 3.5, 0.28), new THREE.Vector3(x0 + dx, 22.1, frontZ + 0.1), materials.stoneDark);
    addBox("pavilion dormer placeholder", new THREE.Vector3(2.4, 2.8, 0.6), new THREE.Vector3(x0 + dx, pavilion.roofY + 1.3, frontZ + 0.2), materials.stoneDark);
  }
  for (const dx of [-12, -6, 0, 6, 12]) {
    addSphere("pavilion roof statue silhouette placeholder", 0.5, new THREE.Vector3(x0 + dx, pavilion.roofY + 4.7, frontZ + 0.4), materials.stoneDark, 10, 6);
    addBox("pavilion statue base placeholder", new THREE.Vector3(0.65, 0.45, 0.5), new THREE.Vector3(x0 + dx, pavilion.roofY + 4.05, frontZ + 0.35), materials.stoneDark);
  }
}

// Facade rhythm is still placeholder, but the window scale is human/building plausible.
for (let i = -96; i <= 96; i += 12) {
  addBox("north facade pilaster placeholder", new THREE.Vector3(0.65, 19, 0.45), new THREE.Vector3(i, 9.5, -79.15), materials.stoneDark);
  for (const y of [6.2, 11.2, 16.1]) {
    addBox("facade window placeholder", new THREE.Vector3(2.15, 3.15, 0.22), new THREE.Vector3(i + 4.2, y, -79.05), materials.stoneDark);
  }
}
for (let z = -68; z <= 44; z += 12) {
  addBox("west wing pilaster placeholder", new THREE.Vector3(0.42, 18, 0.65), new THREE.Vector3(-104.15, 9, z), materials.stoneDark);
  addBox("east wing pilaster placeholder", new THREE.Vector3(0.42, 18, 0.65), new THREE.Vector3(104.15, 9, z), materials.stoneDark);
  for (const y of [6.0, 11.0, 15.8]) {
    addBox("west wing window placeholder", new THREE.Vector3(0.22, 3.0, 2.0), new THREE.Vector3(-104.05, y, z + 4.1), materials.stoneDark);
    addBox("east wing window placeholder", new THREE.Vector3(0.22, 3.0, 2.0), new THREE.Vector3(104.05, y, z + 4.1), materials.stoneDark);
  }
}
for (let i = -98; i <= 98; i += 14) {
  addBox("arcade arch dark opening placeholder", new THREE.Vector3(5.4, 5.8, 0.24), new THREE.Vector3(i, 3.2, -78.9), materials.stoneDark);
  addBox("arcade column left placeholder", new THREE.Vector3(0.45, 5.9, 0.35), new THREE.Vector3(i - 2.9, 3.0, -78.65), materials.stone);
  addBox("arcade column right placeholder", new THREE.Vector3(0.45, 5.9, 0.35), new THREE.Vector3(i + 2.9, 3.0, -78.65), materials.stone);
}
for (const wing of [
  { name: "north", x: 0, z: -78.55, w: 205, yaw: 0 },
  { name: "west", x: -103.55, z: -16, w: 118, yaw: Math.PI / 2 },
  { name: "east", x: 103.55, z: -16, w: 118, yaw: Math.PI / 2 },
]) {
  const alongAxis = wing.yaw === 0 ? "x" : "z";
  for (let i = -Math.floor(wing.w / 2) + 7; i <= Math.floor(wing.w / 2) - 7; i += 14) {
    const px = alongAxis === "x" ? i : wing.x;
    const pz = alongAxis === "x" ? wing.z : wing.z + i;
    addBoxYaw(`${wing.name} facade arcade shadow refined`, new THREE.Vector3(4.5, 5.8, 0.18), new THREE.Vector3(px, 3.25, pz), materials.stoneDark, wing.yaw);
    addBoxYaw(`${wing.name} facade arched stone header refined`, new THREE.Vector3(5.7, 0.45, 0.34), new THREE.Vector3(px, 6.35, pz + (wing.yaw === 0 ? 0.25 : 0)), materials.stone, wing.yaw);
    for (const y of [11.8, 16.8]) {
      addBoxYaw(`${wing.name} facade tall glass refined`, new THREE.Vector3(2.2, 3.7, 0.16), new THREE.Vector3(px, y, pz + (wing.yaw === 0 ? 0.25 : 0)), new THREE.MeshPhysicalMaterial({ color: 0x91a8ad, transparent: true, opacity: 0.38, roughness: 0.18 }), wing.yaw);
      addBoxYaw(`${wing.name} facade window stone frame refined`, new THREE.Vector3(2.8, 4.2, 0.16), new THREE.Vector3(px, y, pz + (wing.yaw === 0 ? 0.18 : 0)), materials.stoneDark, wing.yaw);
      addBoxYaw(`${wing.name} facade window inset refined`, new THREE.Vector3(2.2, 3.6, 0.19), new THREE.Vector3(px, y, pz + (wing.yaw === 0 ? 0.28 : 0)), new THREE.MeshPhysicalMaterial({ color: 0xb9d4d7, transparent: true, opacity: 0.38, roughness: 0.16 }), wing.yaw);
    }
    addBoxYaw(`${wing.name} roof dormer refined`, new THREE.Vector3(2.3, 2.5, 0.6), new THREE.Vector3(px, 24.6, pz + (wing.yaw === 0 ? 0.35 : 0)), materials.stoneDark, wing.yaw);
  }
  addBoxYaw(`${wing.name} long lower cornice refined`, new THREE.Vector3(wing.w, 0.5, 0.55), new THREE.Vector3(wing.x, 7.1, wing.z + (wing.yaw === 0 ? 0.25 : 0)), materials.stoneDark, wing.yaw);
  addBoxYaw(`${wing.name} long upper cornice refined`, new THREE.Vector3(wing.w, 0.55, 0.55), new THREE.Vector3(wing.x, 20.3, wing.z + (wing.yaw === 0 ? 0.25 : 0)), materials.stoneDark, wing.yaw);
  addBoxYaw(`${wing.name} dark mansard roof line refined`, new THREE.Vector3(wing.w, 3.2, 4.2), new THREE.Vector3(wing.x, 23.7, wing.z + (wing.yaw === 0 ? -1.0 : 0)), new THREE.MeshStandardMaterial({ color: 0x2f3540, roughness: 0.64 }), wing.yaw);
}

function addLineSegments(name, points, material) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const lines = new THREE.LineSegments(geometry, material);
  lines.name = name;
  scene.add(lines);
  return lines;
}

function pushSegment(points, a, b) {
  points.push(a.clone(), b.clone());
}

function createSquarePyramid(name, baseSide, height, position, glassMaterial, lineMaterial) {
  const half = baseSide / 2;
  const corners = [
    new THREE.Vector3(-half, 0, half),
    new THREE.Vector3(half, 0, half),
    new THREE.Vector3(half, 0, -half),
    new THREE.Vector3(-half, 0, -half),
  ];
  const apex = new THREE.Vector3(0, height, 0);
  const vertices = [];
  const indices = [];
  for (let i = 0; i < 4; i++) {
    const start = vertices.length / 3;
    const a = corners[i];
    const b = corners[(i + 1) % 4];
    vertices.push(a.x, a.y, a.z, b.x, b.y, b.z, apex.x, apex.y, apex.z);
    indices.push(start, start + 1, start + 2);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, glassMaterial);
  mesh.name = name;
  mesh.position.copy(position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);

  // Fourteen subdivisions across each face produce a calmer, human-readable
  // approximation close to the official total pane count. This is not an
  // engineering reconstruction of all 675 diamond and 118 triangular panes.
  const linePoints = [];
  const rows = 14;
  for (let i = 0; i < 4; i++) {
    const a = corners[i].clone().add(position);
    const b = corners[(i + 1) % 4].clone().add(position);
    const c = apex.clone().add(position);
    pushSegment(linePoints, a, b);
    pushSegment(linePoints, a, c);
    pushSegment(linePoints, b, c);
    const pointAt = (row, col) => {
      const v = row / rows;
      const left = a.clone().lerp(c, v);
      const right = b.clone().lerp(c, v);
      const columns = Math.max(1, rows - row);
      return left.lerp(right, col / columns);
    };
    for (let row = 0; row < rows - 1; row++) {
      const columns = rows - row;
      const nextColumns = columns - 1;
      for (let col = 0; col <= columns; col++) {
        const point = pointAt(row, col);
        if (col <= nextColumns) pushSegment(linePoints, point, pointAt(row + 1, col));
        if (col > 0) pushSegment(linePoints, point, pointAt(row + 1, col - 1));
      }
    }
  }
  addLineSegments(`${name} metal grid`, linePoints, lineMaterial);
  return mesh;
}

// Louvre Pyramid dimensions are bound to the official-source contract.
createSquarePyramid(
  "Louvre Pyramid official scale seed: 21m high, 35m base width",
  louvreContract.scale.main_pyramid.base_width_m,
  louvreContract.scale.main_pyramid.height_m,
  new THREE.Vector3(0, 0, 0),
  materials.glass,
  new THREE.LineBasicMaterial({ color: 0x2b3a3f, transparent: true, opacity: 0.5 }),
);
const entranceGlassMat = new THREE.MeshPhysicalMaterial({ color: 0xd4e5e8, transparent: true, opacity: 0.24, roughness: 0.02, metalness: 0.05, transmission: 0.65 });
addBox("main pyramid recessed entrance fixed glass wall west", new THREE.Vector3(2.85, 2.28, 0.07), new THREE.Vector3(-3.48, 1.14, 18.08), entranceGlassMat);
addBox("main pyramid recessed entrance fixed glass wall east", new THREE.Vector3(2.85, 2.28, 0.07), new THREE.Vector3(3.48, 1.14, 18.08), entranceGlassMat);
addBox("main pyramid entrance thin black sign rail", new THREE.Vector3(8.9, 0.18, 0.11), new THREE.Vector3(0, 2.42, 18.34), materials.sign);
addBox("main pyramid entrance low metal threshold", new THREE.Vector3(8.8, 0.08, 0.18), new THREE.Vector3(0, 0.04, 18.34), materials.metal);
placeSignText("MUSEE DU LOUVRE", new THREE.Vector3(0, 2.5, 18.62), 0, 5.0, 0.3, 92);
const doorMetal = new THREE.MeshStandardMaterial({ color: 0x20282d, roughness: 0.32, metalness: 0.64 });
const doorGlass = new THREE.MeshPhysicalMaterial({ color: 0xd8eef0, transparent: true, opacity: 0.3, roughness: 0.015, transmission: 0.68 });
for (const x of [-4.91, -2.05, 2.05, 4.91]) {
  addBox("pyramid entrance slim dark mullion", new THREE.Vector3(0.045, 2.16, 0.08), new THREE.Vector3(x - 0.52, 1.09, 18.43), doorMetal);
  addBox("pyramid entrance slim dark mullion", new THREE.Vector3(0.045, 2.16, 0.08), new THREE.Vector3(x + 0.52, 1.09, 18.43), doorMetal);
}
addBox("pyramid entrance low dark floor mat", new THREE.Vector3(7.8, 0.018, 1.45), new THREE.Vector3(0, 0.032, 19.25), new THREE.MeshStandardMaterial({ color: 0x33383a, roughness: 0.86 }));
for (const x of [-4.32, -1.42, 1.42, 4.32]) {
  addBox("pyramid entrance side mullion", new THREE.Vector3(0.06, 2.45, 0.14), new THREE.Vector3(x, 1.22, 18.34), doorMetal);
}

// The official Louvre page says there are two smaller Cour Napoleon pyramids.
// Their exact positions and all basin dimensions below remain approximations.
createSquarePyramid("west small Cour Napoleon pyramid approximate placement", 8.2, 5.0, new THREE.Vector3(-38, 0.11, 18), materials.glass, materials.darkMetal);
createSquarePyramid("east small Cour Napoleon pyramid approximate placement", 8.2, 5.0, new THREE.Vector3(38, 0.11, 18), materials.glass, materials.darkMetal);

addReflectingPoolBasin("west reflecting pool approximate", 46, 11, -45, -2);
addReflectingPoolBasin("east reflecting pool approximate", 46, 11, 45, -2);
addReflectingPoolBasin("west small-pyramid pool approximate", 16, 9, -38, 18);
addReflectingPoolBasin("east small-pyramid pool approximate", 16, 9, 38, 18);
for (const [x, z] of [[-45, -2], [45, -2], [38, 18], [-38, 18]]) {
  addCylinder("fountain jet placeholder", 0.08, 5.4, new THREE.Vector3(x, 2.7, z), new THREE.MeshBasicMaterial({ color: 0xdef7ff, transparent: true, opacity: 0.48 }), 10);
}

// The categories/colors come from the current official entrance page. The
// lane geometry and convergence are deliberately labeled approximate.
const queueLaneMaterials = [
  new THREE.MeshBasicMaterial({ color: 0x4c9b67, transparent: true, opacity: 0.16 }),
  new THREE.MeshBasicMaterial({ color: 0xe18a3b, transparent: true, opacity: 0.16 }),
  new THREE.MeshBasicMaterial({ color: 0x3f78b7, transparent: true, opacity: 0.16 }),
];
for (const [index, x] of [-5.35, 0, 5.35].entries()) {
  addPlane(`official queue category approximate lane ${index + 1}`, 4.85, 18, new THREE.Vector3(x, 0.052, 35), queueLaneMaterials[index]);
}
for (const x of [-8, -2.7, 2.7, 8]) addStanchionLineZ(x, 26, 44, 7);
placeSignText("TICKET / PASS", new THREE.Vector3(-5.35, 1.45, 44.2), 0, 3.8, 0.42, 54);
placeSignText("NO TICKET", new THREE.Vector3(0, 1.45, 44.2), 0, 3.8, 0.42, 54);
placeSignText("PRIORITY", new THREE.Vector3(5.35, 1.45, 44.2), 0, 3.8, 0.42, 54);

// Visitor placeholders are only for explicit scale/AI review. They are hidden during normal architecture review.
if (showActors) {
  for (const [x, z] of [[-18, 34], [-12, 39], [-5, 33], [6, 38], [14, 34], [22, 42], [-46, 22], [48, 23]]) {
    addVisitor({
      actor_id: `generic_visitor_${x}_${z}`,
      display_name: "",
      spawn: { x, y: 0, z, heading_degrees: x > 0 ? -12 : 12 },
      appearance: { jacket: ["#5b6570", "#6d4a42", "#3f5d48", "#746a55"][Math.abs(x + z) % 4], shirt: "#ece8dd", pants: "#242831" },
    });
  }
}

// Louvre under-pyramid interior pass. The failed bakery prototype has been removed from the live scene.
function makeMat(color, roughness = 0.82, metalness = 0) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness });
}

function addBoxRot(name, size, position, material, rotation) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(size.x, size.y, size.z), material);
  mesh.name = name;
  mesh.position.copy(position);
  mesh.rotation.copy(rotation);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

const interiorMats = {
  floor: new THREE.MeshPhysicalMaterial({ color: 0xbfc1bc, roughness: 0.22, metalness: 0.02, clearcoat: 0.35 }),
  concrete: makeMat(0xc9c0ad, 0.88),
  concreteDark: makeMat(0x8d8475, 0.86),
  warmWall: makeMat(0x9b8163, 0.9),
  blackSign: makeMat(0x17191b, 0.58),
  escalator: makeMat(0x4f565a, 0.42, 0.28),
  railGlass: new THREE.MeshPhysicalMaterial({ color: 0xb9dfe3, transparent: true, opacity: 0.28, roughness: 0.04, transmission: 0.4, side: THREE.DoubleSide }),
  light: new THREE.MeshBasicMaterial({ color: 0xfff2c8 }),
};

function addInteriorStairs(name, x, z, yaw, up = true) {
  const stepCount = 22;
  for (let i = 0; i < stepCount; i++) {
    const t = i / (stepCount - 1);
    const localZ = THREE.MathUtils.lerp(-7.6, 7.6, t);
    const y = THREE.MathUtils.lerp(-9.55, -2.2, up ? t : 1 - t);
    const cx = x + Math.sin(yaw) * localZ;
    const cz = z + Math.cos(yaw) * localZ;
    addBoxYaw(`${name} step ${i}`, new THREE.Vector3(4.4, 0.16, 0.52), new THREE.Vector3(cx, y, cz), interiorMats.concrete, yaw);
  }
  addBoxYaw(`${name} glass rail left`, new THREE.Vector3(0.08, 1.1, 16.2), new THREE.Vector3(x - Math.cos(yaw) * 2.35, -5.7, z), interiorMats.railGlass, yaw);
  addBoxYaw(`${name} glass rail right`, new THREE.Vector3(0.08, 1.1, 16.2), new THREE.Vector3(x + Math.cos(yaw) * 2.35, -5.7, z), interiorMats.railGlass, yaw);
}

function addEscalator(name, x, z, yaw) {
  addBoxRot(`${name} sloped body`, new THREE.Vector3(2.2, 0.34, 17.4), new THREE.Vector3(x, -5.55, z), interiorMats.escalator, new THREE.Euler(-0.45, yaw, 0));
  addBoxRot(`${name} glass side left`, new THREE.Vector3(0.08, 1.0, 17.4), new THREE.Vector3(x - Math.cos(yaw) * 1.25, -5.15, z), interiorMats.railGlass, new THREE.Euler(-0.45, yaw, 0));
  addBoxRot(`${name} glass side right`, new THREE.Vector3(0.08, 1.0, 17.4), new THREE.Vector3(x + Math.cos(yaw) * 1.25, -5.15, z), interiorMats.railGlass, new THREE.Euler(-0.45, yaw, 0));
}

function addSpiralRamp() {
  const points = [];
  const turns = 1.35;
  let previous = null;
  for (let i = 0; i <= 96; i++) {
    const t = i / 96;
    const angle = t * Math.PI * 2 * turns - Math.PI * 0.3;
    const r = 6.5 + t * 0.9;
    const p = new THREE.Vector3(19 + Math.cos(angle) * r, THREE.MathUtils.lerp(-9.2, -2.4, t), -1 + Math.sin(angle) * r);
    if (previous) {
      const mid = previous.clone().lerp(p, 0.5);
      const len = previous.distanceTo(p);
      const yaw = Math.atan2(p.x - previous.x, p.z - previous.z);
      addBoxYaw("under pyramid spiral ramp segment", new THREE.Vector3(3.0, 0.16, len), mid, interiorMats.concrete, yaw);
      addBoxYaw("under pyramid spiral ramp glass rail", new THREE.Vector3(0.08, 0.9, len), mid.clone().add(new THREE.Vector3(Math.cos(yaw) * 1.55, 0.45, -Math.sin(yaw) * 1.55)), interiorMats.railGlass, yaw);
    }
    previous = p;
    points.push(p);
  }
}

function buildLouvreInterior() {
  addPlane("under pyramid polished stone floor", 88, 70, new THREE.Vector3(0, -10.05, 9), interiorMats.floor);
  addBox("under pyramid upper visitor deck slab", new THREE.Vector3(38, 1.2, 22), new THREE.Vector3(0, -2.4, 2), interiorMats.concrete);
  addBox("under pyramid central square support pier", new THREE.Vector3(4.2, 8.4, 4.2), new THREE.Vector3(0, -6.25, 2), interiorMats.concrete);
  for (const [x, z] of [[-31, -14], [31, -14], [-31, 28], [31, 28]]) {
    addBox("under pyramid rectangular concrete column", new THREE.Vector3(2.6, 8.2, 2.6), new THREE.Vector3(x, -6.0, z), interiorMats.concrete);
  }
  for (let x = -17.5; x <= 17.5; x += 5) {
    for (let z = -7.5; z <= 11; z += 4.7) {
      addBox("under pyramid coffered ceiling recess", new THREE.Vector3(3.5, 0.22, 3.2), new THREE.Vector3(x, -3.08, z), interiorMats.concreteDark);
    }
  }
  for (let x = -35; x <= 35; x += 7) {
    addBox("under pyramid polished floor seam north south", new THREE.Vector3(0.035, 0.018, 67), new THREE.Vector3(x, -10.01, 9), materials.pavingB);
  }
  for (let z = -24; z <= 42; z += 7) {
    addBox("under pyramid polished floor seam east west", new THREE.Vector3(86, 0.018, 0.035), new THREE.Vector3(0, -10.0, z), materials.pavingB);
  }
  addBox("under pyramid west wall mass", new THREE.Vector3(25, 5.2, 1.2), new THREE.Vector3(-30, -7.25, -21), interiorMats.warmWall);
  addBox("under pyramid east wall mass", new THREE.Vector3(25, 5.2, 1.2), new THREE.Vector3(30, -7.25, -21), interiorMats.warmWall);
  addBox("under pyramid ticket hall back wall", new THREE.Vector3(36, 5.2, 1.2), new THREE.Vector3(0, -7.25, -24), interiorMats.warmWall);
  addBox("under pyramid louvre lens black sign", new THREE.Vector3(12, 1.1, 0.18), new THREE.Vector3(10, -6.1, -23.35), interiorMats.blackSign);
  placeLabel("Le Louvre", new THREE.Vector3(10, -6.05, -23.2), 0, 8.5, 0.8, 46, { fixed: true, alwaysVisible: true });
  addInteriorStairs("under pyramid broad left stair", -20, 4, -0.75, true);
  addInteriorStairs("under pyramid broad right stair", 20, 4, 0.75, true);
  addEscalator("under pyramid rear escalator pair left", -9, -11, 0.1);
  addEscalator("under pyramid rear escalator pair right", -5.8, -11, 0.1);
  addSpiralRamp();
  for (let x = -38; x <= 38; x += 4) {
    addBox("under pyramid queue post", new THREE.Vector3(0.09, 1.0, 0.09), new THREE.Vector3(x, -9.5, 31), materials.metal);
    if (x < 38) addBox("under pyramid queue belt", new THREE.Vector3(3.2, 0.05, 0.05), new THREE.Vector3(x + 2, -9.0, 31), materials.rope);
  }
  for (const [x, z] of [[-24, 20], [-15, 28], [-3, 24], [11, 31], [24, 21], [31, 8], [-31, 5], [6, -15], [18, -18], [-18, -18]]) {
    addVisitor({
      actor_id: `under_pyramid_visitor_${x}_${z}`,
      display_name: "",
      spawn: { x, y: -10.05, z, heading_degrees: x > 0 ? -25 : 25 },
      appearance: { jacket: "#384857", shirt: "#e8e1d2", pants: "#252525" },
    });
  }
  const lineMat = new THREE.LineBasicMaterial({ color: 0x1f3035, transparent: true, opacity: 0.7 });
  const lattice = [];
  for (let x = -17.5; x <= 17.5; x += 3.5) {
    pushSegment(lattice, new THREE.Vector3(x, 0.25, -17.5), new THREE.Vector3(0, 21, 0));
    pushSegment(lattice, new THREE.Vector3(x, 0.25, 17.5), new THREE.Vector3(0, 21, 0));
  }
  for (let z = -17.5; z <= 17.5; z += 3.5) {
    pushSegment(lattice, new THREE.Vector3(-17.5, 0.25, z), new THREE.Vector3(0, 21, 0));
    pushSegment(lattice, new THREE.Vector3(17.5, 0.25, z), new THREE.Vector3(0, 21, 0));
  }
  addLineSegments("under pyramid interior glass lattice emphasis", lattice, lineMat);
  placeLabel("Under-pyramid lobby draft: polished stone floor, concrete deck, columns, stairs/escalators, spiral ramp, and glass lattice are now the active next pass.", new THREE.Vector3(-33, -5.4, 37), 0.42, 13.5, 2.0, 34);
}

// Disabled from live rendering: the under-pyramid interior must be rebuilt from official maps
// and section blueprints before it appears in the walkable world again.
// buildLouvreInterior();

// Bounded r4 circulation cells. These are intentionally separate from the old
// full-lobby draft above. They reproduce only forms visible in Robert-supplied
// photos: an entrance threshold, concrete deck/columns/coffers, a spiral stair,
// and visible escalator forms. Exact dimensions, routing, elevators, galleries,
// rooms, and artwork remain absent.
const APPROXIMATE_SPIRAL = Object.freeze({
  center_x: 0,
  center_z: 8,
  radius_m: 5.4,
  width_m: 2.35,
  start_angle_rad: 0,
  end_angle_rad: Math.PI * 1.5,
  top_floor_y_m: 0,
  lower_floor_y_m: -8,
});

const louvreReviewRuntime = {
  streamingPromise: Promise.resolve(null),
  streamingRequestSerial: 0,
  lastStreamingRequest: null,
  lastSurface: { floor_y_m: 0, cell_id: "cour_napoleon_exterior", kind: "exterior" },
  thresholdBlockedCount: 0,
  stairSamples: [],
};

function addCellBox(group, name, size, position, material, rotation = null) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(size.x, size.y, size.z), material);
  mesh.name = name;
  mesh.position.copy(position);
  if (rotation) mesh.rotation.copy(rotation);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  return mesh;
}

function createApproximatePyramidEntranceCell(priorState = null) {
  const group = new THREE.Group();
  group.name = "CELL pyramid_entrance_transition - approximate owner-review geometry";
  group.visible = false;
  const restoredProgress = THREE.MathUtils.clamp(Number(priorState?.door_progress ?? 0), 0, 1);
  const restoredTarget = priorState?.door_target === "open" ? 1 : 0;
  const state = {
    door_progress: restoredProgress,
    door_target: restoredTarget,
    phase: restoredProgress >= 0.94 ? "open" : restoredProgress <= 0.06 ? "closed" : "paused",
    threshold_collision_solid: restoredProgress < 0.94,
    operation_count: Math.max(0, Number(priorState?.operation_count || 0)),
  };
  const left = addCellBox(
    group,
    "approximate streamed entrance sliding leaf left",
    new THREE.Vector3(1.38, 2.16, 0.07),
    new THREE.Vector3(-0.71, 1.1, 18.39),
    doorGlass,
  );
  const right = addCellBox(
    group,
    "approximate streamed entrance sliding leaf right",
    new THREE.Vector3(1.38, 2.16, 0.07),
    new THREE.Vector3(0.71, 1.1, 18.39),
    doorGlass,
  );
  const leftHandle = addCellBox(group, "approximate entrance left handle", new THREE.Vector3(0.045, 0.72, 0.09), new THREE.Vector3(-0.18, 1.08, 18.48), doorMetal);
  const rightHandle = addCellBox(group, "approximate entrance right handle", new THREE.Vector3(0.045, 0.72, 0.09), new THREE.Vector3(0.18, 1.08, 18.48), doorMetal);
  const thresholdLight = new THREE.PointLight(0xffe2a7, 1.2, 8, 2);
  thresholdLight.name = "approximate entrance threshold light";
  thresholdLight.position.set(0, 2.2, 16.8);
  group.add(thresholdLight);
  const module = {
    ready: true,
    collision_ready: true,
    metrics: { asset_bytes: 196608, triangles: 256, texture_bytes: 0, draw_calls: 6 },
    group,
    state,
    left,
    right,
    leftHandle,
    rightHandle,
  };
  updateApproximateDoorMeshes(module);
  return module;
}

function updateApproximateDoorMeshes(module) {
  if (!module) return;
  const travel = 1.42 * module.state.door_progress;
  module.left.position.x = -0.71 - travel;
  module.right.position.x = 0.71 + travel;
  module.leftHandle.position.x = -0.18 - travel;
  module.rightHandle.position.x = 0.18 + travel;
  module.state.threshold_collision_solid = module.state.door_progress < 0.94;
}

function createApproximateUnderPyramidCirculationCell(priorState = null) {
  const group = new THREE.Group();
  group.name = "CELL under_pyramid_level_minus_2_circulation - bounded approximate blockout";
  group.visible = false;
  const warmConcrete = new THREE.MeshStandardMaterial({ color: 0xc8beaa, roughness: 0.88 });
  const darkerConcrete = new THREE.MeshStandardMaterial({ color: 0x8e887d, roughness: 0.9 });
  const lowerFloor = new THREE.MeshPhysicalMaterial({ color: 0xb8bab6, roughness: 0.3, clearcoat: 0.22 });
  const railGlass = new THREE.MeshPhysicalMaterial({ color: 0xb9dfe3, transparent: true, opacity: 0.28, roughness: 0.04, transmission: 0.36 });
  const escalatorMaterial = new THREE.MeshStandardMaterial({ color: 0x4a5155, roughness: 0.42, metalness: 0.3 });

  addCellBox(group, "approximate upper entrance landing", new THREE.Vector3(3.0, 0.16, 5.6), new THREE.Vector3(0, -0.08, 15.7), warmConcrete);
  addCellBox(group, "approximate bounded lower circulation floor", new THREE.Vector3(36, 0.22, 21), new THREE.Vector3(0, -8.12, 0.5), lowerFloor);
  for (const [x, z] of [[-14, -7], [14, -7], [-14, 8], [14, 8]]) {
    addCellBox(group, "approximate photo-supported concrete column", new THREE.Vector3(1.5, 6.2, 1.5), new THREE.Vector3(x, -5.0, z), warmConcrete);
  }
  for (let x = -12; x <= 12; x += 4) {
    for (let z = -6; z <= 6; z += 4) {
      addCellBox(group, "approximate coffered deck underside panel", new THREE.Vector3(3.3, 0.26, 3.3), new THREE.Vector3(x, -1.55, z), darkerConcrete);
    }
  }
  addCellBox(group, "locked Richelieu/Sully/Denon continuation wall", new THREE.Vector3(36, 4.8, 0.6), new THREE.Vector3(0, -5.6, -10.2), darkerConcrete);

  const stepCount = 40;
  for (let index = 0; index < stepCount; index += 1) {
    const t = index / (stepCount - 1);
    const angle = THREE.MathUtils.lerp(APPROXIMATE_SPIRAL.start_angle_rad, APPROXIMATE_SPIRAL.end_angle_rad, t);
    const nextAngle = THREE.MathUtils.lerp(APPROXIMATE_SPIRAL.start_angle_rad, APPROXIMATE_SPIRAL.end_angle_rad, Math.min(1, (index + 1) / (stepCount - 1)));
    const x = APPROXIMATE_SPIRAL.center_x + Math.sin(angle) * APPROXIMATE_SPIRAL.radius_m;
    const z = APPROXIMATE_SPIRAL.center_z + Math.cos(angle) * APPROXIMATE_SPIRAL.radius_m;
    const floorY = THREE.MathUtils.lerp(APPROXIMATE_SPIRAL.top_floor_y_m, APPROXIMATE_SPIRAL.lower_floor_y_m, t);
    const arcLength = Math.max(0.5, APPROXIMATE_SPIRAL.radius_m * Math.abs(nextAngle - angle) + 0.12);
    const yaw = Math.atan2(Math.cos(angle), -Math.sin(angle));
    addCellBox(
      group,
      `approximate walkable spiral stair step ${String(index + 1).padStart(2, "0")}`,
      new THREE.Vector3(APPROXIMATE_SPIRAL.width_m, 0.18, arcLength),
      new THREE.Vector3(x, floorY - 0.09, z),
      warmConcrete,
      new THREE.Euler(0, yaw, 0),
    );
    if (index % 2 === 0) {
      for (const radialOffset of [-APPROXIMATE_SPIRAL.width_m / 2 - 0.08, APPROXIMATE_SPIRAL.width_m / 2 + 0.08]) {
        const railRadius = APPROXIMATE_SPIRAL.radius_m + radialOffset;
        addCellBox(
          group,
          "approximate spiral stair glass guard segment",
          new THREE.Vector3(0.08, 0.95, arcLength * 2.05),
          new THREE.Vector3(
            APPROXIMATE_SPIRAL.center_x + Math.sin(angle) * railRadius,
            floorY + 0.42,
            APPROXIMATE_SPIRAL.center_z + Math.cos(angle) * railRadius,
          ),
          railGlass,
          new THREE.Euler(0, yaw, 0),
        );
      }
    }
  }

  for (const x of [6.5, 9.2]) {
    const escalatorBody = addCellBox(
      group,
      "visible-only approximate escalator blockout - non-operable",
      new THREE.Vector3(2.1, 0.38, 13.5),
      new THREE.Vector3(x, -4.2, 1.2),
      escalatorMaterial,
      new THREE.Euler(-0.56, 0, 0),
    );
    escalatorBody.userData.louvre_runtime_kind = "visible_only_escalator_blockout";
    addCellBox(group, "visible-only escalator glass side", new THREE.Vector3(0.08, 0.9, 13.5), new THREE.Vector3(x - 1.08, -3.75, 1.2), railGlass, new THREE.Euler(-0.56, 0, 0));
    addCellBox(group, "visible-only escalator glass side", new THREE.Vector3(0.08, 0.9, 13.5), new THREE.Vector3(x + 1.08, -3.75, 1.2), railGlass, new THREE.Euler(-0.56, 0, 0));
  }
  const light = new THREE.PointLight(0xffedc2, 2.5, 55, 2);
  light.name = "bounded circulation review light";
  light.position.set(0, -2.1, 2);
  group.add(light);
  return {
    ready: true,
    collision_ready: true,
    metrics: { asset_bytes: 1048576, triangles: 9000, texture_bytes: 0, draw_calls: 105 },
    group,
    state: {
      visit_count: Math.max(0, Number(priorState?.visit_count || 0)),
      last_floor_y_m: Number.isFinite(Number(priorState?.last_floor_y_m)) ? Number(priorState.last_floor_y_m) : 0,
    },
    escalator_blockers: [
      { center_x: 6.5, center_z: 1.2, half_x: 1.55, half_z: 7.1 },
      { center_x: 9.2, center_z: 1.2, half_x: 1.55, half_z: 7.1 },
    ],
  };
}

function registerLouvreReviewCells() {
  louvreCellStreaming.registerCell("cour_napoleon_exterior", {
    async load() {
      return {
        ready: true,
        collision_ready: true,
        metrics: { asset_bytes: 6291456, triangles: 80000, texture_bytes: 3145728, draw_calls: 500 },
        eager_geometry: true,
      };
    },
    async preflightUnload() {},
    async unload() {},
    async captureState() {
      return { eager_geometry_preserved: true };
    },
  });
  louvreCellStreaming.registerCell("pyramid_entrance_transition", {
    async load({ prior_state: priorState }) {
      return createApproximatePyramidEntranceCell(priorState);
    },
    async validate(module) {
      if (module.group.children.length < 5) throw new Error("Approximate entrance staged without both door leaves and threshold light.");
    },
    async commit(module) {
      module.group.visible = true;
      scene.add(module.group);
    },
    async preflightUnload(module) {
      if (!module?.group) throw new Error("Approximate entrance cannot unload without its staged group/state.");
    },
    async unload(module) {
      scene.remove(module.group);
      module.group.visible = false;
    },
    async rollback(module) {
      scene.remove(module.group);
      module.group.visible = false;
    },
    async captureState(module) {
      return {
        door_progress: Number(module.state.door_progress.toFixed(4)),
        door_target: module.state.door_target >= 0.5 ? "open" : "closed",
        operation_count: module.state.operation_count,
      };
    },
  });
  louvreCellStreaming.registerCell("under_pyramid_level_minus_2_circulation", {
    async load({ prior_state: priorState }) {
      return createApproximateUnderPyramidCirculationCell(priorState);
    },
    async validate(module) {
      const stairSteps = module.group.children.filter((item) => item.name.startsWith("approximate walkable spiral stair step"));
      if (stairSteps.length !== 40) throw new Error("The bounded circulation cell staged an incomplete spiral stair.");
      if (module.group.children.some((item) => /elevator/i.test(item.name))) throw new Error("Unsupported elevator geometry entered the bounded circulation cell.");
    },
    async commit(module) {
      module.state.visit_count += 1;
      module.group.visible = true;
      scene.add(module.group);
    },
    async preflightUnload(module) {
      if (!module?.group || !Number.isFinite(module.state.last_floor_y_m)) throw new Error("Approximate circulation cannot unload without persistent state.");
    },
    async unload(module) {
      scene.remove(module.group);
      module.group.visible = false;
    },
    async rollback(module) {
      scene.remove(module.group);
      module.group.visible = false;
    },
    async captureState(module) {
      return {
        visit_count: module.state.visit_count,
        last_floor_y_m: module.state.last_floor_y_m,
      };
    },
  });
}

function louvreStreamingPosition(position = controls.object.position) {
  return [[position.x, position.y, position.z]];
}

function requestLouvreStreamingForPosition(position = controls.object.position, force = false) {
  if (!soloLouvreMode) return Promise.resolve(null);
  const point = [Number(position.x), Number(position.y), Number(position.z)];
  if (!force && louvreReviewRuntime.lastStreamingRequest && Math.hypot(
    point[0] - louvreReviewRuntime.lastStreamingRequest[0],
    point[1] - louvreReviewRuntime.lastStreamingRequest[1],
    point[2] - louvreReviewRuntime.lastStreamingRequest[2],
  ) < 1.5) return louvreReviewRuntime.streamingPromise;
  louvreReviewRuntime.lastStreamingRequest = point;
  const serial = ++louvreReviewRuntime.streamingRequestSerial;
  louvreReviewRuntime.streamingPromise = louvreCellStreaming.apply([point]).then((snapshot) => {
    if (serial === louvreReviewRuntime.streamingRequestSerial && window.__louvreNotebookDebug) {
      window.__louvreNotebookDebug.streaming = snapshot;
    }
    return snapshot;
  });
  return louvreReviewRuntime.streamingPromise;
}

function currentEntranceCell() {
  return louvreCellStreaming.getLoadedModule("pyramid_entrance_transition");
}

function currentCirculationCell() {
  return louvreCellStreaming.getLoadedModule("under_pyramid_level_minus_2_circulation");
}

function entranceThresholdPassable() {
  const entrance = currentEntranceCell();
  return Boolean(entrance && currentCirculationCell() && entrance.state.door_progress >= 0.94 && !entrance.state.threshold_collision_solid);
}

async function ensureApproximateCirculationReady() {
  louvreCellStreaming.authorizeCell("under_pyramid_level_minus_2_circulation");
  const snapshot = await requestLouvreStreamingForPosition(new THREE.Vector3(0, 1.68, 17), true);
  const required = ["cour_napoleon_exterior", "pyramid_entrance_transition", "under_pyramid_level_minus_2_circulation"];
  return Boolean(snapshot?.transaction?.ok && required.every((id) => snapshot.managed_loaded_cells.includes(id)));
}

function thresholdOccupied(position = controls.object.position) {
  return Math.abs(position.x) < 1.7 && position.z > 17.35 && position.z < 19.25;
}

async function setApproximateEntranceDoorTarget(open) {
  if (!await ensureApproximateCirculationReady()) {
    statusEl.textContent = "Entrance remains solid: the bounded destination cell did not validate, so the last proven cell stayed loaded.";
    return false;
  }
  const entrance = currentEntranceCell();
  if (!entrance) return false;
  if (!open && thresholdOccupied()) {
    statusEl.textContent = "The approximate entrance will not close while the owner-review camera occupies its threshold.";
    return false;
  }
  entrance.state.door_target = open ? 1 : 0;
  entrance.state.operation_count += 1;
  entrance.state.phase = open ? "opening" : "closing";
  statusEl.textContent = open
    ? "Opening the approximate photo-supported entrance. Collision stays solid until the leaves are at least 94% open and the destination cell is ready."
    : "Closing the approximate entrance; the threshold becomes solid immediately.";
  return true;
}

async function toggleApproximateEntrance() {
  const entrance = currentEntranceCell();
  const open = entrance ? entrance.state.door_target < 0.5 || !currentCirculationCell() : true;
  return setApproximateEntranceDoorTarget(open);
}

function updateApproximateEntrance(delta) {
  const entrance = currentEntranceCell();
  if (!entrance) return;
  const previous = entrance.state.door_progress;
  const step = delta / 0.6;
  entrance.state.door_progress = THREE.MathUtils.clamp(
    entrance.state.door_progress + Math.sign(entrance.state.door_target - entrance.state.door_progress) * Math.min(step, Math.abs(entrance.state.door_target - entrance.state.door_progress)),
    0,
    1,
  );
  if (entrance.state.door_target < 0.5) entrance.state.threshold_collision_solid = true;
  updateApproximateDoorMeshes(entrance);
  if (entrance.state.door_progress >= 0.999) entrance.state.phase = "open";
  else if (entrance.state.door_progress <= 0.001) entrance.state.phase = "closed";
  else if (entrance.state.door_progress !== previous) entrance.state.phase = entrance.state.door_target >= 0.5 ? "opening" : "closing";
}

function spiralSampleAt(x, z) {
  const dx = x - APPROXIMATE_SPIRAL.center_x;
  const dz = z - APPROXIMATE_SPIRAL.center_z;
  const radius = Math.hypot(dx, dz);
  let angle = Math.atan2(dx, dz);
  if (angle < 0) angle += Math.PI * 2;
  const withinWidth = Math.abs(radius - APPROXIMATE_SPIRAL.radius_m) <= APPROXIMATE_SPIRAL.width_m * 0.58;
  const withinArc = angle >= APPROXIMATE_SPIRAL.start_angle_rad - 0.06 && angle <= APPROXIMATE_SPIRAL.end_angle_rad + 0.06;
  if (!withinWidth || !withinArc) return null;
  const progress = THREE.MathUtils.clamp(
    (angle - APPROXIMATE_SPIRAL.start_angle_rad) / (APPROXIMATE_SPIRAL.end_angle_rad - APPROXIMATE_SPIRAL.start_angle_rad),
    0,
    1,
  );
  return {
    progress,
    floor_y_m: THREE.MathUtils.lerp(APPROXIMATE_SPIRAL.top_floor_y_m, APPROXIMATE_SPIRAL.lower_floor_y_m, progress),
    radius_m: radius,
    angle_rad: angle,
  };
}

function resolveApproximateLouvreSurface(x, z, previousFloorY = louvreReviewRuntime.lastSurface.floor_y_m) {
  const underCell = currentCirculationCell();
  const insidePyramidFootprint = Math.abs(x) < 17.5 && Math.abs(z) < 17.5;
  if (!insidePyramidFootprint || z >= 17.25) {
    return { floor_y_m: 0, cell_id: "cour_napoleon_exterior", kind: "exterior" };
  }
  if (Math.abs(x) <= 1.48 && z >= 13.0 && z < 17.55) {
    if (!entranceThresholdPassable()) return null;
    return { floor_y_m: 0, cell_id: "pyramid_entrance_transition", kind: "upper_landing" };
  }
  if (!underCell) return null;
  const stair = spiralSampleAt(x, z);
  if (stair) {
    return { ...stair, cell_id: "under_pyramid_level_minus_2_circulation", kind: "walkable_spiral_stair" };
  }
  const atBottomLanding = x >= -7.2 && x <= -3.4 && z >= 6.3 && z <= 9.7;
  const inLowerFloor = x >= -18 && x <= 18 && z >= -9.8 && z <= 11;
  if (inLowerFloor && (previousFloorY <= -7.2 || atBottomLanding && previousFloorY <= -6.6)) {
    for (const blocker of underCell.escalator_blockers) {
      if (Math.abs(x - blocker.center_x) < blocker.half_x && Math.abs(z - blocker.center_z) < blocker.half_z) return null;
    }
    return { floor_y_m: -8, cell_id: "under_pyramid_level_minus_2_circulation", kind: "lower_circulation" };
  }
  return null;
}

function applyApproximateLouvreSurface(obj, previousPosition) {
  const previousFloor = previousPosition.y - louvreContract.scale.eye_height_m;
  const surface = resolveApproximateLouvreSurface(obj.position.x, obj.position.z, previousFloor);
  if (!surface) {
    obj.position.copy(previousPosition);
    louvreReviewRuntime.thresholdBlockedCount += 1;
    const message = entranceThresholdPassable()
      ? "The bounded approximate circulation path ends here; elevators, galleries, rooms, artwork, and unsourced lobby areas remain solid and unloaded."
      : "The approximate Pyramid threshold is solid until both destination cells validate and the door reaches its open collision state.";
    statusEl.textContent = message;
    recordReviewCollision(entranceThresholdPassable() ? "bounded_circulation_edge" : "approximate_entrance_threshold", message);
    return false;
  }
  obj.position.y = surface.floor_y_m + louvreContract.scale.eye_height_m;
  louvreReviewRuntime.lastSurface = surface;
  if (surface.kind === "walkable_spiral_stair") {
    const samples = louvreReviewRuntime.stairSamples;
    samples.push({ progress: Number(surface.progress.toFixed(4)), floor_y_m: Number(surface.floor_y_m.toFixed(4)) });
    if (samples.length > 160) samples.splice(0, samples.length - 160);
  }
  const circulation = currentCirculationCell();
  if (circulation) circulation.state.last_floor_y_m = surface.floor_y_m;
  return true;
}

placeLabel("VR scale pass: Louvre source says the Pyramid is 21 m high with a 35 m base. Eye height is 1.68 m and movement is human walking speed.", new THREE.Vector3(-31, 5.5, 24), 0.45, 13, 2.2, 38);
placeLabel("Palace facades are massing placeholders. Need public photos, maps, facade references, and license review before detail work.", new THREE.Vector3(-70, 7.2, -64), 0.15, 13.5, 2.3, 36);
placeLabel("Community-photo intake is queued: Wikimedia category/file leads are recorded, but images are not treated as blueprints.", new THREE.Vector3(46, 5.2, 36), -0.5, 12.5, 2.1, 36);
placeLabel("Future expansion: enter museum interiors only after floor plans/photos are sourced; unknown rooms stay unknown.", new THREE.Vector3(65, 7.2, -64), -0.18, 12.5, 2.1, 36);
placeLabel("Paris Notebook World anchor: later Paris locations can be positioned by real-world distance from this Louvre seed.", new THREE.Vector3(-73, 4.8, 45), 0.6, 12.5, 2.1, 36);
placeLabel("Robert-supplied photos now guide: exterior glass density, pools/fountains, queue stanchions, pavilion roofs, and under-pyramid interior next.", new THREE.Vector3(38, 6.8, 55), -0.55, 12.5, 2.1, 35);

if (soloLouvreMode) {
  for (const marker of louvreContract.in_world_truth_markers) placeTruthMarker(marker);
  setTruthMarkersVisible(true);
}

// Walkable boundary hints.
const boundaryMat = new THREE.MeshBasicMaterial({ color: 0xd7c071, transparent: true, opacity: 0.55 });
addBox("prototype boundary north", new THREE.Vector3(230, 1, 0.2), new THREE.Vector3(0, 0.5, -90), boundaryMat);
addBox("prototype boundary south", new THREE.Vector3(230, 1, 0.2), new THREE.Vector3(0, 0.5, 90), boundaryMat);
addBox("prototype boundary west", new THREE.Vector3(0.2, 1, 180), new THREE.Vector3(-115, 0.5, 0), boundaryMat);
addBox("prototype boundary east", new THREE.Vector3(0.2, 1, 180), new THREE.Vector3(115, 0.5, 0), boundaryMat);

function pointInsideContractCollider(x, z, collider, clearance = 0) {
  if (collider.kind !== "rect") return false;
  const [centerX, centerZ] = collider.center;
  const [halfX, halfZ] = collider.half_extents;
  return Math.abs(x - centerX) < halfX + clearance && Math.abs(z - centerZ) < halfZ + clearance;
}

function collisionAt(x, z, clearance = avatarClearanceRadius) {
  for (const collider of louvreContract.colliders) {
    if (pointInsideContractCollider(x, z, collider, clearance)) return collider;
  }
  return null;
}

function runStaticRouteChecks() {
  return louvreContract.routes.map((route) => {
    let samples = 0;
    for (let index = 0; index < route.points.length - 1; index++) {
      const [ax, az] = route.points[index];
      const [bx, bz] = route.points[index + 1];
      const distance = Math.hypot(bx - ax, bz - az);
      const steps = Math.max(1, Math.ceil(distance / 0.25));
      for (let step = 0; step <= steps; step++) {
        samples += 1;
        const t = step / steps;
        const x = THREE.MathUtils.lerp(ax, bx, t);
        const z = THREE.MathUtils.lerp(az, bz, t);
        const collider = collisionAt(x, z);
        if (collider) {
          return { id: route.id, status: "blocked", collider_id: collider.id, sample: [Number(x.toFixed(3)), Number(z.toFixed(3))], samples };
        }
      }
    }
    return { id: route.id, status: "clear", collider_id: null, sample: null, samples };
  });
}

function measureRouteAt(route, x, z) {
  if (!route || route.points.length < 2) return null;
  let totalLength = 0;
  let traversedBeforeSegment = 0;
  let nearestDistance = Infinity;
  let nearestAlong = 0;
  let nearestPoint = [route.points[0][0], route.points[0][1]];
  for (let index = 0; index < route.points.length - 1; index++) {
    const [ax, az] = route.points[index];
    const [bx, bz] = route.points[index + 1];
    const dx = bx - ax;
    const dz = bz - az;
    const lengthSquared = dx * dx + dz * dz;
    const segmentLength = Math.sqrt(lengthSquared);
    const t = lengthSquared > 0
      ? THREE.MathUtils.clamp(((x - ax) * dx + (z - az) * dz) / lengthSquared, 0, 1)
      : 0;
    const projectedX = ax + dx * t;
    const projectedZ = az + dz * t;
    const distance = Math.hypot(x - projectedX, z - projectedZ);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestAlong = traversedBeforeSegment + segmentLength * t;
      nearestPoint = [projectedX, projectedZ];
    }
    traversedBeforeSegment += segmentLength;
    totalLength += segmentLength;
  }
  const progress = totalLength > 0 ? nearestAlong / totalLength : 0;
  return {
    route_id: route.id,
    method: louvreContract.review_measurements.route_progress_method,
    total_length_m: Number(totalLength.toFixed(2)),
    along_route_m: Number(nearestAlong.toFixed(2)),
    remaining_route_m: Number(Math.max(0, totalLength - nearestAlong).toFixed(2)),
    progress_0_to_1: Number(progress.toFixed(4)),
    progress_percent: Number((progress * 100).toFixed(1)),
    cross_track_distance_m: Number(nearestDistance.toFixed(2)),
    nearest_route_point_m: nearestPoint.map((value) => Number(value.toFixed(3))),
  };
}

function activeRouteMeasurement() {
  const route = louvreContract.routes[activeReviewRouteIndex] || null;
  const position = controls.object.position;
  return measureRouteAt(route, position.x, position.z);
}

function recordReviewCollision(colliderId, message, { force = false } = {}) {
  if (!soloLouvreMode || !colliderId) return false;
  const now = Date.now();
  const debounce = louvreContract.review_measurements.collision_event_debounce_ms;
  if (!force && now - (collisionDebounceAt.get(colliderId) || 0) < debounce) return false;
  collisionDebounceAt.set(colliderId, now);
  reviewSessionMetrics.collision_events += 1;
  reviewSessionMetrics.collision_by_id[colliderId] = (reviewSessionMetrics.collision_by_id[colliderId] || 0) + 1;
  reviewSessionMetrics.last_collision_id = colliderId;
  reviewSessionMetrics.last_collision_message = message || null;
  reviewSessionMetrics.last_collision_at = new Date(now).toISOString();
  updateReviewMetricDisplay(true);
  return true;
}

function reviewMetricsSnapshot() {
  const position = controls.object.position;
  return {
    session_started_at: reviewSessionMetrics.started_at,
    session_elapsed_seconds: Number(((Date.now() - Date.parse(reviewSessionMetrics.started_at)) / 1000).toFixed(2)),
    viewer_position_m: [position.x, position.y, position.z].map((value) => Number(value.toFixed(3))),
    distance_walked_m: Number(reviewSessionMetrics.distance_walked_m.toFixed(2)),
    collision_events: reviewSessionMetrics.collision_events,
    collision_by_id: { ...reviewSessionMetrics.collision_by_id },
    last_collision_id: reviewSessionMetrics.last_collision_id,
    last_collision_message: reviewSessionMetrics.last_collision_message,
    last_collision_at: reviewSessionMetrics.last_collision_at,
    active_route: activeRouteMeasurement(),
  };
}

let lastReviewMetricUpdateAt = 0;
function updateReviewMetricDisplay(force = false) {
  if (!soloLouvreMode) return;
  const now = performance.now();
  if (!force && now - lastReviewMetricUpdateAt < 150) return;
  lastReviewMetricUpdateAt = now;
  const measurement = activeRouteMeasurement();
  if (routeMetricEl) {
    routeMetricEl.textContent = measurement
      ? `Route: ${measurement.progress_percent.toFixed(1)}% · ${measurement.remaining_route_m.toFixed(2)} m remaining · ${measurement.cross_track_distance_m.toFixed(2)} m off line`
      : "Route: press R to select a measured guide route";
  }
  if (walkMetricEl) walkMetricEl.textContent = `Walked: ${reviewSessionMetrics.distance_walked_m.toFixed(2)} m this review session`;
  if (collisionMetricEl) {
    collisionMetricEl.textContent = reviewSessionMetrics.collision_events
      ? `Collisions: ${reviewSessionMetrics.collision_events} · last ${reviewSessionMetrics.last_collision_id}`
      : "Collisions: 0 declared review contacts";
  }
}

function setReviewRoute(index) {
  if (!soloLouvreMode) return false;
  if (activeReviewRouteLine) {
    scene.remove(activeReviewRouteLine);
    activeReviewRouteLine.traverse((child) => {
      child.geometry?.dispose?.();
      if (child.material && !Array.isArray(child.material)) child.material.dispose?.();
    });
  }
  activeReviewRouteIndex = THREE.MathUtils.euclideanModulo(index, louvreContract.routes.length);
  const route = louvreContract.routes[activeReviewRouteIndex];
  const group = new THREE.Group();
  group.name = `review route:${route.id}`;
  const points = route.points.map(([x, z]) => new THREE.Vector3(x, 0.18, z));
  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({ color: 0xf2c45e, transparent: true, opacity: 0.92 }),
  );
  group.add(line);
  for (const [pointIndex, point] of points.entries()) {
    const marker = new THREE.Mesh(
      new THREE.CylinderGeometry(pointIndex === points.length - 1 ? 0.38 : 0.22, pointIndex === points.length - 1 ? 0.38 : 0.22, 0.08, 18),
      new THREE.MeshBasicMaterial({ color: pointIndex === points.length - 1 ? 0x4fa875 : 0xf2c45e }),
    );
    marker.position.copy(point);
    group.add(marker);
  }
  scene.add(group);
  activeReviewRouteLine = group;
  const check = runStaticRouteChecks().find((item) => item.id === route.id);
  const measurement = activeRouteMeasurement();
  statusEl.textContent = `Guide route ${activeReviewRouteIndex + 1}/${louvreContract.routes.length}: ${route.label}. Static clearance: ${check?.status || "unknown"}; length ${measurement?.total_length_m.toFixed(2) || "unknown"} m. The gold line does not move you.`;
  updateReviewMetricDisplay(true);
  return true;
}

function cycleReviewRoute() {
  return setReviewRoute(activeReviewRouteIndex + 1);
}

function updateNearestLandmark() {
  if (!soloLouvreMode || !landmarkStatusEl) return;
  const position = controls.object.position;
  let nearest = null;
  let nearestDistance = Infinity;
  for (const landmark of louvreContract.landmarks) {
    const [x, , z] = landmark.position;
    const distance = Math.hypot(position.x - x, position.z - z);
    if (distance < nearestDistance) {
      nearest = landmark;
      nearestDistance = distance;
    }
  }
  currentNearestLandmark = nearest;
  landmarkStatusEl.textContent = nearest
    ? `Nearest: ${nearest.label} · ${nearestDistance.toFixed(1)} m · ${nearest.truth.replaceAll("_", " ")}`
    : "Nearest landmark: unavailable";
}

function setWalkPosition(x, z, { recordRejected = false } = {}) {
  if (!Number.isFinite(x) || !Number.isFinite(z)) return false;
  if (x < -108 || x > 108 || z < -84 || z > 84) {
    if (recordRejected) recordReviewCollision("review_boundary", "The solo review boundary rejected this position.", { force: true });
    return false;
  }
  const collider = collisionAt(x, z);
  if (collider) {
    if (recordRejected) recordReviewCollision(collider.id, collider.message, { force: true });
    return false;
  }
  controls.object.position.set(x, louvreContract.scale.eye_height_m, z);
  updateNearestLandmark();
  updateReviewMetricDisplay(true);
  return true;
}

function resetSceneForTardisPreview() {
  for (const child of [...scene.children]) {
    if (child === controls.object || child.isLight) continue;
    scene.remove(child);
  }
  scene.background = new THREE.Color(0x08111d);
  scene.fog = new THREE.Fog(0x08111d, 70, 210);
  tardisState.doorOpen = false;
  tardisState.exteriorGroup = null;
  tardisState.exteriorObjects = [];
  tardisState.consoleScreen = null;
  tardisState.frontDoorLeft = null;
  tardisState.frontDoorRight = null;
  tardisState.consolePreview = null;
  showTardisConsolePanel(false);
}

function resetSceneForStandaloneWorld(background = 0xd8dde0) {
  for (const child of [...scene.children]) {
    if (child === controls.object || child.isLight) continue;
    scene.remove(child);
  }
  scene.background = new THREE.Color(background);
  scene.fog = new THREE.Fog(background, 190, 820);
  tardisState.doorOpen = false;
  tardisState.exteriorGroup = null;
  tardisState.exteriorObjects = [];
  tardisState.consoleScreen = null;
  tardisState.frontDoorLeft = null;
  tardisState.frontDoorRight = null;
  tardisState.consolePreview = null;
  showTardisConsolePanel(false);
}

function makeTardisConsoleTexture() {
  const worlds = tardisNotebookWorlds;
  const activeWorld = selectedTardisNotebookWorld();
  const active = selectedTardisDestination();
  const parkedExit = returnAreaLabel();
  const canvas2d = document.createElement("canvas");
  canvas2d.width = 1600;
  canvas2d.height = 950;
  const ctx = canvas2d.getContext("2d");
  ctx.fillStyle = "#05172b";
  ctx.fillRect(0, 0, canvas2d.width, canvas2d.height);
  ctx.strokeStyle = "#1db7ff";
  ctx.lineWidth = 8;
  ctx.strokeRect(18, 18, canvas2d.width - 36, canvas2d.height - 36);
  ctx.fillStyle = "#66d7ff";
  ctx.font = "700 76px Arial";
  ctx.textAlign = "center";
  ctx.fillText("TARDIS WORLD CONSOLE", canvas2d.width / 2, 100);
  ctx.font = "34px Arial";
  ctx.textAlign = "left";
  ctx.fillText("Current Location: TARDIS Gateway", 70, 165);
  ctx.fillText("Current User: Robert", 610, 165);
  ctx.fillText(`Exit Door: ${parkedExit}`, 1070, 165);

  const tabs = ["Notebook Worlds", "Talk Command", "World Builder", "Memory Rebuild"];
  ctx.font = "700 34px Arial";
  for (let i = 0; i < tabs.length; i++) {
    const y = 240 + i * 82;
    ctx.fillStyle = i === 0 ? "rgba(0,145,255,0.38)" : "rgba(0,70,130,0.35)";
    ctx.fillRect(70, y - 44, 340, 60);
    ctx.strokeStyle = "#168bd6";
    ctx.lineWidth = 3;
    ctx.strokeRect(70, y - 44, 340, 60);
    ctx.fillStyle = "#bfefff";
    ctx.fillText(tabs[i], 105, y - 5);
  }

  ctx.fillStyle = "#09213d";
  ctx.fillRect(455, 196, 620, 600);
  ctx.strokeStyle = "#168bd6";
  ctx.strokeRect(455, 196, 620, 600);
  ctx.fillStyle = "#66d7ff";
  ctx.fillText("NOTEBOOK WORLDS", 510, 240);
  ctx.font = "32px Arial";
  for (let i = 0; i < worlds.length; i++) {
    const world = worlds[i];
    const y = 315 + i * 88;
    ctx.fillStyle = i === tardisState.selectedNotebookWorld ? "rgba(0,145,255,0.45)" : "rgba(0,30,70,0.42)";
    ctx.fillRect(490, y - 52, 540, 68);
    ctx.strokeStyle = i === tardisState.selectedNotebookWorld ? "#66d7ff" : "#145e93";
    ctx.strokeRect(490, y - 52, 540, 68);
    ctx.fillStyle = "#d8f6ff";
    ctx.fillText(`${i + 1}. ${world.title}`, 510, y - 22);
    ctx.fillStyle = "#69cfff";
    ctx.fillText(`${world.status}`, 510, y + 12);
  }
  if (activeWorld.largeMap && activeWorld.areas?.length) {
    ctx.fillStyle = "#66d7ff";
    ctx.font = "700 30px Arial";
    ctx.fillText("Paris areas", 510, 720);
    ctx.font = "28px Arial";
    activeWorld.areas.forEach((area, i) => {
      const x = 510 + i * 265;
      ctx.fillStyle = i === tardisState.selectedNotebookArea ? "rgba(0,145,255,0.42)" : "rgba(0,45,92,0.42)";
      ctx.fillRect(x, 745, 245, 48);
      ctx.strokeStyle = "#44c4ff";
      ctx.strokeRect(x, 745, 245, 48);
      ctx.fillStyle = "#d8f6ff";
      ctx.fillText(area.title.replace(" / Pyramid", ""), x + 12, 778);
    });
  }

  ctx.fillStyle = "#09213d";
  ctx.fillRect(1120, 196, 410, 600);
  ctx.strokeStyle = "#168bd6";
  ctx.strokeRect(1120, 196, 410, 600);
  ctx.fillStyle = "#66d7ff";
  ctx.font = "700 34px Arial";
  ctx.fillText("ROUTE DETAILS", 1160, 240);
  ctx.font = "30px Arial";
  const detailLines = [
    `World: ${active.notebookTitle || active.title}`,
    `Area: ${active.title}`,
    `Type: ${activeWorld.type}`,
    `Status: ${activeWorld.status}`,
    `Progress: ${active.progress}`,
    `Source: ${active.source}`,
    "Access: permanent users only",
    `Travel: ${active.travelReady ? "ready" : "talk/build first"}`,
    `Plain exit: ${parkedExit}`,
  ];
  detailLines.forEach((line, i) => ctx.fillText(line, 1160, 305 + i * 58));

  ctx.font = "700 30px Arial";
  ctx.fillStyle = "rgba(0,145,255,0.34)";
  ctx.fillRect(70, 835, 1460, 64);
  ctx.strokeStyle = "#44c4ff";
  ctx.strokeRect(70, 835, 1460, 64);
  ctx.fillStyle = "#d8f6ff";
  ctx.fillText("Talk button: take me to Paris, create the Enterprise D, take me to the Chinese Theatre, rebuild a college memory", 95, 877);
  const texture = new THREE.CanvasTexture(canvas2d);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function setConsoleScreenTexture() {
  if (!tardisState.consoleScreen) return;
  tardisState.consoleScreen.material.map?.dispose();
  tardisState.consoleScreen.material.map = makeTardisConsoleTexture();
  tardisState.consoleScreen.material.needsUpdate = true;
  updateTardisConsolePanel();
}

function ensureTardisConsolePanel() {
  if (tardisConsolePanel) return tardisConsolePanel;
  const panel = document.createElement("section");
  panel.id = "tardisConsoleControls";
  panel.setAttribute("aria-label", "TARDIS world console");
  panel.innerHTML = `
    <div class="tardis-console-header">
      <strong>World Console</strong>
      <span id="tardisParkedExit"></span>
    </div>
    <div id="tardisWorldButtons" class="tardis-destination-buttons"></div>
    <div id="tardisAreaButtons" class="tardis-area-buttons"></div>
    <div id="tardisSelectedDetails" class="tardis-selected-details"></div>
    <form class="tardis-talk-form" aria-label="Talk to TARDIS">
      <input id="tardisTalkText" type="text" autocomplete="off" placeholder="take me to Paris, create the Enterprise D..." />
      <button type="submit" data-tardis-talk>Talk</button>
    </form>
  `;
  panel.addEventListener("click", (event) => {
    event.stopPropagation();
    const worldButton = event.target.closest("[data-tardis-world]");
    if (worldButton) {
      selectTardisNotebookWorld(Number(worldButton.dataset.tardisWorld));
      return;
    }
    const areaButton = event.target.closest("[data-tardis-area]");
    if (areaButton) {
      selectTardisNotebookArea(Number(areaButton.dataset.tardisArea), { travel: true });
      return;
    }
  });
  panel.addEventListener("submit", (event) => {
    event.preventDefault();
    event.stopPropagation();
    beginTardisTalk();
  });
  panel.addEventListener("mousedown", (event) => event.stopPropagation());
  document.body.appendChild(panel);
  tardisConsolePanel = panel;
  return panel;
}

function updateTardisConsolePanel() {
  if (!tardisConsolePanel) return;
  const selected = selectedTardisDestination();
  const selectedWorld = selectedTardisNotebookWorld();
  const exitEl = tardisConsolePanel.querySelector("#tardisParkedExit");
  const worldEl = tardisConsolePanel.querySelector("#tardisWorldButtons");
  const areaEl = tardisConsolePanel.querySelector("#tardisAreaButtons");
  const detailEl = tardisConsolePanel.querySelector("#tardisSelectedDetails");
  exitEl.textContent = `Exit door: ${returnAreaLabel()}`;
  worldEl.innerHTML = "";
  for (let i = 0; i < tardisNotebookWorlds.length; i++) {
    const world = tardisNotebookWorlds[i];
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.tardisWorld = String(i);
    button.className = i === tardisState.selectedNotebookWorld ? "selected" : "";
    button.textContent = world.title;
    if (!world.travelReady && !world.largeMap) button.classList.add("locked");
    worldEl.appendChild(button);
  }
  areaEl.innerHTML = "";
  areaEl.hidden = !(selectedWorld.largeMap && selectedWorld.areas?.length > 1);
  if (!areaEl.hidden) {
    for (let i = 0; i < selectedWorld.areas.length; i++) {
      const area = selectedWorld.areas[i];
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.tardisArea = String(i);
      button.className = i === tardisState.selectedNotebookArea ? "selected" : "";
      button.textContent = area.title;
      areaEl.appendChild(button);
    }
  }
  if (selectedWorld.largeMap) {
    const reviewWarning = selected.ownerReviewOnly
      ? " Owner-only solo review: no person is activated, and unbuilt doors/interiors/galleries stay locked."
      : "";
    detailEl.textContent = `${selected.title}: ${selected.status} - ${selected.progress}. ${selected.source}.${reviewWarning} Paris is large; only the selected nearby area should load as cell modules are completed.`;
  } else if (selectedWorld.id === "new_notebook_world") {
    detailEl.textContent = "Use Talk to request a new notebook world. The World Builder will gather sources and wait for approval before it becomes a travel button.";
  } else if (selectedWorld.id === "memory_reconstruction") {
    detailEl.textContent = "Use Talk to name the memory. The TARDIS will create a private reconstruction request and mark unknown details instead of guessing.";
  } else {
    detailEl.textContent = `${selected.notebookTitle || selected.title}: ${selected.status} - ${selected.progress}. Click the world button to travel, or say 'take me to library'.`;
  }
}

function showTardisConsolePanel(show) {
  const panel = ensureTardisConsolePanel();
  panel.classList.toggle("visible", !!show);
  if (show) updateTardisConsolePanel();
}

function focusTardisTalkInput(message) {
  const input = ensureTardisConsolePanel().querySelector("#tardisTalkText");
  if (message) statusEl.textContent = message;
  input?.focus();
}

function selectTardisNotebookWorld(index) {
  if (!Number.isFinite(index)) return;
  setTardisSelection(index, 0);
  const world = selectedTardisNotebookWorld();
  setConsoleScreenTexture();
  if (world.largeMap && world.areas?.length > 1) {
    statusEl.textContent = `${world.title} selected. Choose Louvre or Place des Vosges, or say the exact Paris area.`;
    return;
  }
  if (world.travelReady) {
    travelToDestination(selectedTardisDestination());
    return;
  }
  focusTardisTalkInput(`${world.title} needs a spoken or typed request before the World Builder can start.`);
}

function selectTardisNotebookArea(index, options = {}) {
  if (!Number.isFinite(index)) return;
  setTardisSelection(tardisState.selectedNotebookWorld, index);
  setConsoleScreenTexture();
  const destination = selectedTardisDestination();
  if (options.travel) {
    travelToDestination(destination);
    return;
  }
  statusEl.textContent = `${destination.title} selected inside ${destination.notebookTitle}.`;
}

function selectTardisDestination(index) {
  if (!Number.isFinite(index)) return;
  tardisState.selectedDestination = THREE.MathUtils.clamp(Math.trunc(index), 0, tardisDestinations.length - 1);
  const destination = selectedTardisDestination();
  tardisState.selectedNotebookWorld = destination.worldIndex || 0;
  tardisState.selectedNotebookArea = destination.areaIndex || 0;
  tardisState.previewedDestination = null;
  setConsoleScreenTexture();
  statusEl.textContent = `${destination.title} selected. Press Enter to travel, or use Talk for a new place or memory.`;
}

function previewSelectedDestination() {
  const destination = selectedTardisDestination();
  tardisState.previewedDestination = destination.area;
  setConsoleScreenTexture();
  statusEl.textContent = `${destination.title}: ${destination.status}, ${destination.progress}. ${destination.source}. This preview did not move the TARDIS.`;
}

function saveTardisTalkRequest(entry) {
  const storageKey = "kira_tardis_talk_requests";
  let requests = [];
  try {
    requests = JSON.parse(localStorage.getItem(storageKey) || "[]");
  } catch {
    requests = [];
  }
  requests.push(entry);
  localStorage.setItem(storageKey, JSON.stringify(requests.slice(-50)));
}

function queueTardisBuildRequest(command, requestType, title) {
  const entry = {
    createdAt: new Date().toISOString(),
    command,
    requestType,
    title,
    status: "queued_for_world_builder_review",
    sourcePolicy: "no blueprint, no build; unknown details must stay labeled unknown",
    approvalRequired: true,
  };
  saveTardisTalkRequest(entry);
  tardisState.lastTalkRequest = entry;
  setConsoleScreenTexture();
  statusEl.textContent = `${title} request queued for the World Builder. It will need sources and Robert approval before it becomes a travel destination.`;
  return entry;
}

function routeTardisToArea(area) {
  const index = tardisDestinations.findIndex((destination) => destination.area === area || destination.shellLocation === area);
  if (index < 0) return false;
  selectTardisDestination(index);
  travelToDestination(selectedTardisDestination());
  return true;
}

function handleTardisCommand(rawCommand) {
  const command = String(rawCommand || "").trim();
  if (!command) {
    focusTardisTalkInput("Type a destination or request, or press Talk again after entering words.");
    return null;
  }
  const lower = command.toLowerCase();
  if (/\b(library|public library)\b/.test(lower)) return routeTardisToArea("library");
  if (/\b(home|house|home world)\b/.test(lower) && !/\b(rebuild|create|build|memory)\b/.test(lower)) return routeTardisToArea("home");
  if (/\b(louvre|pyramid)\b/.test(lower)) return routeTardisToArea("louvre");
  if (/\b(vosges|place des vosges)\b/.test(lower)) return routeTardisToArea("vosges");
  if (/\bparis\b/.test(lower)) {
    const parisIndex = tardisNotebookWorlds.findIndex((world) => world.id === "paris_notebook_world");
    setTardisSelection(parisIndex, 0);
    setConsoleScreenTexture();
    statusEl.textContent = "Paris is a large notebook world. Choose Louvre or Place des Vosges, or say the exact area.";
    return { action: "choose_paris_area" };
  }
  if (/\b(memory|remember|reconstruct|college|school|job corp|blockbuster|uncle sam jam|childhood)\b/.test(lower)) {
    return queueTardisBuildRequest(command, "memory_reconstruction", "Memory Reconstruction");
  }
  if (/\b(create|build|make|rebuild|enterprise|starship|chinese theatre|chinese theater|hollywood|gotham|dc)\b/.test(lower)) {
    const title = /\benterprise\b/.test(lower)
      ? "Enterprise D Notebook World"
      : /\b(chinese theatre|chinese theater|hollywood)\b/.test(lower)
        ? "Chinese Theatre Hollywood Notebook World"
        : "New Notebook World";
    return queueTardisBuildRequest(command, "notebook_world_build", title);
  }
  return queueTardisBuildRequest(command, "travel_or_build_request", "Unrecognized TARDIS Request");
}

function beginTardisTalk() {
  const input = ensureTardisConsolePanel().querySelector("#tardisTalkText");
  const typed = input?.value?.trim() || "";
  if (typed) {
    handleTardisCommand(typed);
    input.value = "";
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    focusTardisTalkInput("Speech recognition is not available here. Type the TARDIS request and press Talk.");
    return;
  }
  statusEl.textContent = "Listening for a TARDIS command.";
  const recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onresult = (event) => {
    const spoken = event.results?.[0]?.[0]?.transcript || "";
    if (input) input.value = spoken;
    handleTardisCommand(spoken);
  };
  recognition.onerror = () => focusTardisTalkInput("I could not hear the TARDIS command. Type it instead.");
  recognition.start();
}

function buildPoliceBoxExterior(spawn = new THREE.Vector3(0, 0, 0)) {
  const group = new THREE.Group();
  group.name = "TARDIS exterior blue police box gateway";
  scene.add(group);
  tardisState.exteriorGroup = group;
  tardisState.exteriorObjects = [];
  const track = (mesh) => {
    tardisState.exteriorObjects.push(mesh);
    group.add(mesh);
    return mesh;
  };
  const blue = new THREE.MeshStandardMaterial({ color: 0x163a57, roughness: 0.78, metalness: 0.05 });
  const darkBlue = new THREE.MeshStandardMaterial({ color: 0x0d2235, roughness: 0.82 });
  const black = new THREE.MeshStandardMaterial({ color: 0x05070a, roughness: 0.55 });
  const litGlass = new THREE.MeshBasicMaterial({ color: 0xdff7ff });
  const paper = new THREE.MeshBasicMaterial({ color: 0xe9e4d8 });
  const half = 0.8;
  track(addBox("TARDIS stone base", new THREE.Vector3(1.85, 0.16, 1.85), new THREE.Vector3(0, 0.08, 0), darkBlue));
  for (const [x, z] of [[0, 0], [-half, 0], [half, 0], [0, -half], [0, half]]) {
    const size = x === 0 && z === 0 ? new THREE.Vector3(1.55, 2.78, 1.55) : new THREE.Vector3(x ? 0.13 : 1.75, 2.95, z ? 0.13 : 1.75);
    const pos = new THREE.Vector3(x, 1.55, z);
    const mesh = addBox("TARDIS blue timber wall/pillar", size, pos, blue);
    track(mesh);
  }
  track(addBox("TARDIS roof step lower", new THREE.Vector3(1.95, 0.2, 1.95), new THREE.Vector3(0, 3.08, 0), darkBlue));
  track(addBox("TARDIS roof step upper", new THREE.Vector3(1.6, 0.24, 1.6), new THREE.Vector3(0, 3.3, 0), darkBlue));
  track(addCylinder("TARDIS lamp glass", 0.14, 0.42, new THREE.Vector3(0, 3.68, 0), litGlass, 18));
  track(addCylinder("TARDIS lamp cap", 0.17, 0.06, new THREE.Vector3(0, 3.92, 0), darkBlue, 18));
  for (const z of [0.95, -0.95]) {
    track(addBox("TARDIS police public call box sign", new THREE.Vector3(1.75, 0.22, 0.06), new THREE.Vector3(0, 2.72, z), black));
    track(placeSignText("POLICE  PUBLIC CALL  BOX", new THREE.Vector3(0, 2.735, z + Math.sign(z) * 0.045), z > 0 ? 0 : Math.PI, 1.46, 0.11, 52));
  }
  for (const x of [0.95, -0.95]) {
    track(addBox("TARDIS side police sign", new THREE.Vector3(0.06, 0.22, 1.75), new THREE.Vector3(x, 2.72, 0), black));
  }
  for (const x of [-0.34, 0.34]) {
    const door = track(addBox("TARDIS front openable door slab", new THREE.Vector3(0.62, 2.16, 0.055), new THREE.Vector3(x, 1.38, 0.97), blue));
    if (x < 0) tardisState.frontDoorLeft = door;
    else tardisState.frontDoorRight = door;
    for (const y of [0.7, 1.24, 1.78]) {
      track(addBox("TARDIS front door recessed panel", new THREE.Vector3(0.4, 0.32, 0.045), new THREE.Vector3(x, y, 1.015), darkBlue));
    }
    for (const wx of [-0.2, 0.2]) {
      track(addBox("TARDIS glowing window pane", new THREE.Vector3(0.15, 0.32, 0.05), new THREE.Vector3(x + wx * 0.62, 2.25, 1.025), litGlass));
    }
  }
  track(addBox("TARDIS telephone notice", new THREE.Vector3(0.32, 0.46, 0.05), new THREE.Vector3(-0.52, 1.52, 1.03), paper));
  track(addBox("TARDIS round door handle", new THREE.Vector3(0.055, 0.055, 0.045), new THREE.Vector3(0.09, 1.2, 1.06), new THREE.MeshStandardMaterial({ color: 0xb8a56b, roughness: 0.35, metalness: 0.6 })));
  const preview = new THREE.Group();
  preview.name = "TARDIS exterior visible bigger-inside console preview";
  preview.visible = false;
  const inside = new THREE.Mesh(new THREE.BoxGeometry(1.04, 1.9, 0.08), new THREE.MeshStandardMaterial({ color: 0x020913, roughness: 0.86 }));
  inside.name = "TARDIS dark interior visible through open doors";
  inside.position.set(0, 1.38, 1.01);
  preview.add(inside);
  const screen = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.34, 0.045), new THREE.MeshBasicMaterial({ color: 0x00a6ff }));
  screen.name = "TARDIS tiny working console screen preview";
  screen.position.set(0, 1.62, 1.07);
  preview.add(screen);
  const rotor = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 1.05, 16), new THREE.MeshBasicMaterial({ color: 0x51bfff }));
  rotor.name = "TARDIS tiny time rotor preview";
  rotor.position.set(0, 1.42, 1.1);
  preview.add(rotor);
  group.add(preview);
  tardisState.consolePreview = preview;
  group.position.copy(spawn);
  setTardisExteriorDoorOpen(false);
  return group;
}

function setTardisExteriorDoorOpen(open) {
  tardisState.doorOpen = !!open;
  if (tardisState.frontDoorLeft) {
    tardisState.frontDoorLeft.rotation.y = tardisState.doorOpen ? 1.18 : 0;
    tardisState.frontDoorLeft.position.set(tardisState.doorOpen ? -0.66 : -0.34, 1.38, tardisState.doorOpen ? 1.1 : 0.97);
  }
  if (tardisState.frontDoorRight) {
    tardisState.frontDoorRight.rotation.y = tardisState.doorOpen ? -1.18 : 0;
    tardisState.frontDoorRight.position.set(tardisState.doorOpen ? 0.66 : 0.34, 1.38, tardisState.doorOpen ? 1.1 : 0.97);
  }
  if (tardisState.consolePreview) tardisState.consolePreview.visible = tardisState.doorOpen;
  for (const mesh of tardisState.exteriorObjects) {
    const name = mesh.name || "";
    if (
      name.includes("TARDIS front door recessed panel") ||
      name.includes("TARDIS glowing window pane") ||
      name.includes("TARDIS telephone notice") ||
      name.includes("TARDIS round door handle")
    ) {
      mesh.visible = !tardisState.doorOpen;
    }
  }
}

function buildTardisInterior() {
  const centerZ = -82;
  const dark = new THREE.MeshStandardMaterial({ color: 0x111a24, roughness: 0.55, metalness: 0.45 });
  const panel = new THREE.MeshStandardMaterial({ color: 0x182739, roughness: 0.5, metalness: 0.55 });
  const blueGlow = new THREE.MeshBasicMaterial({ color: 0x008cff });
  const glassBlue = new THREE.MeshPhysicalMaterial({ color: 0x51bfff, transparent: true, opacity: 0.35, roughness: 0.03, transmission: 0.35 });
  addPlane("TARDIS interior circular metal floor", 54, 54, new THREE.Vector3(0, 0, centerZ), dark);
  for (const r of [8, 15, 22]) addTorus("TARDIS interior blue floor ring", r, 0.055, new THREE.Vector3(0, 0.06, centerZ), blueGlow, new THREE.Euler(Math.PI / 2, 0, 0), 8, 96);
  for (let i = 0; i < 24; i++) {
    const a = (i / 24) * Math.PI * 2;
    const x = Math.cos(a) * 27;
    const z = centerZ + Math.sin(a) * 27;
    addBoxYaw("TARDIS ribbed wall segment", new THREE.Vector3(2.0, 8.0, 0.55), new THREE.Vector3(x, 4.0, z), panel, -a + Math.PI / 2);
    if (i % 2 === 0) addBoxYaw("TARDIS blue wall light", new THREE.Vector3(1.2, 0.18, 0.08), new THREE.Vector3(Math.cos(a) * 26.4, 4.8, centerZ + Math.sin(a) * 26.4), blueGlow, -a + Math.PI / 2);
  }
  for (const a of [Math.PI * 0.05, Math.PI * 0.36, Math.PI * 0.64, Math.PI * 0.95, Math.PI * 1.45]) {
    const x = Math.cos(a) * 25.7;
    const z = centerZ + Math.sin(a) * 25.7;
    addTorus("TARDIS blue circular wall portal", 2.05, 0.08, new THREE.Vector3(x, 3.2, z), blueGlow, new THREE.Euler(0, -a + Math.PI / 2, 0), 12, 72);
    addTorus("TARDIS inner star-map portal ring", 1.36, 0.035, new THREE.Vector3(x, 3.2, z), blueGlow, new THREE.Euler(0, -a + Math.PI / 2, 0), 8, 48);
  }
  for (const [x, z, yaw] of [[-18, centerZ - 10, 0.42], [18, centerZ - 10, -0.42], [-18, centerZ + 9, -0.35], [18, centerZ + 9, 0.35]]) {
    addBoxYaw("TARDIS side workstation desk", new THREE.Vector3(5.4, 0.55, 1.2), new THREE.Vector3(x, 1.05, z), panel, yaw);
    addBoxYaw("TARDIS side workstation blue screen", new THREE.Vector3(3.8, 1.75, 0.12), new THREE.Vector3(x, 2.15, z - 0.55), blueGlow, yaw);
    addBoxYaw("TARDIS side workstation rail", new THREE.Vector3(5.8, 0.14, 0.16), new THREE.Vector3(x, 1.55, z + 1.05), blueGlow, yaw);
  }
  addCylinder("TARDIS central console base", 3.6, 1.15, new THREE.Vector3(0, 0.58, centerZ), panel, 8);
  addCylinder("TARDIS time rotor glass tube", 0.92, 7.0, new THREE.Vector3(0, 4.55, centerZ), glassBlue, 32);
  addCylinder("TARDIS time rotor blue core", 0.38, 7.3, new THREE.Vector3(0, 4.55, centerZ), blueGlow, 18);
  addTorus("TARDIS console top ring", 3.9, 0.12, new THREE.Vector3(0, 1.35, centerZ), blueGlow, new THREE.Euler(Math.PI / 2, 0, 0), 8, 72);
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const x = Math.cos(a) * 4.2;
    const z = centerZ + Math.sin(a) * 4.2;
    addBoxYaw("TARDIS radial console wing", new THREE.Vector3(3.6, 0.35, 1.45), new THREE.Vector3(x, 1.12, z), panel, -a);
    addBoxYaw("TARDIS console blue control strip", new THREE.Vector3(1.7, 0.04, 0.1), new THREE.Vector3(x, 1.34, z), blueGlow, -a);
  }
  const screenMaterial = new THREE.MeshBasicMaterial({ map: makeTardisConsoleTexture(), side: THREE.DoubleSide });
  tardisState.consoleScreen = new THREE.Mesh(new THREE.PlaneGeometry(9.4, 5.6), screenMaterial);
  tardisState.consoleScreen.name = "TARDIS world console persistent gateway screen";
  tardisState.consoleScreen.position.set(0, 3.55, centerZ + 9.2);
  tardisState.consoleScreen.rotation.x = -0.08;
  scene.add(tardisState.consoleScreen);
  addBox("TARDIS console frame", new THREE.Vector3(10.2, 6.2, 0.22), new THREE.Vector3(0, 3.55, centerZ + 9.05), panel);
  addBox("TARDIS persistent shelf/book ledge", new THREE.Vector3(6.5, 0.28, 1.1), new THREE.Vector3(-14, 1.55, centerZ - 12), panel);
  addBox("TARDIS persistent book placeholder", new THREE.Vector3(0.7, 0.14, 1.0), new THREE.Vector3(-15.8, 1.82, centerZ - 12), new THREE.MeshStandardMaterial({ color: 0x6d2b2f, roughness: 0.75 }));
  addBox("TARDIS persistent notebook placeholder", new THREE.Vector3(0.9, 0.12, 1.15), new THREE.Vector3(-14.7, 1.82, centerZ - 12), new THREE.MeshStandardMaterial({ color: 0x1f4f80, roughness: 0.75 }));
  addBox("TARDIS Robert check-in screen", new THREE.Vector3(4.5, 2.5, 0.18), new THREE.Vector3(16, 2.9, centerZ - 11), new THREE.MeshBasicMaterial({ color: 0x062e4f }));
  placeSignText("ROBERT CHECK-IN SCREEN", new THREE.Vector3(16, 3.45, centerZ - 10.86), Math.PI, 3.5, 0.28, 52);
  const returnArea = safeReturnArea();
  const returnLabel = returnArea === "home" ? "HOME WORLD" : returnArea === "library" ? "PUBLIC LIBRARY" : returnArea === "vosges" ? "PLACE DES VOSGES" : "LOUVRE";
  const exteriorTint = returnArea === "home" || returnArea === "library" ? 0x9fd47f : 0xd2c39b;
  addBox("TARDIS interior exit door frame", new THREE.Vector3(4.9, 3.25, 0.2), new THREE.Vector3(0, 1.72, centerZ + 25.0), panel);
  addBox("TARDIS interior exit view to parked world", new THREE.Vector3(3.55, 2.35, 0.08), new THREE.Vector3(0, 1.62, centerZ + 25.14), new THREE.MeshBasicMaterial({ color: exteriorTint }));
  addBox("TARDIS interior open threshold", new THREE.Vector3(4.4, 0.1, 1.0), new THREE.Vector3(0, 0.08, centerZ + 24.55), blueGlow);
  placeSignText(`EXIT TO ${returnLabel}`, new THREE.Vector3(0, 2.75, centerZ + 24.83), Math.PI, 3.5, 0.28, 52);
  addPointLightsForTardis(centerZ);
}

function addPointLightsForTardis(centerZ) {
  for (const [x, y, z, intensity] of [[0, 6, centerZ, 18], [-16, 4, centerZ + 12, 7], [16, 4, centerZ + 12, 7], [-16, 4, centerZ - 12, 7], [16, 4, centerZ - 12, 7]]) {
    const light = new THREE.PointLight(0x1aa7ff, intensity, 45);
    light.position.set(x, y, z);
    scene.add(light);
  }
}

function buildTardisGatewayPreview() {
  resetSceneForTardisPreview();
  scene.add(new THREE.HemisphereLight(0x89c7ff, 0x02060a, 1.2));
  const key = new THREE.DirectionalLight(0xb9dfff, 2.2);
  key.position.set(-8, 12, 12);
  scene.add(key);
  if (requestedView === "interior") {
    buildTardisInterior();
    tardisState.inside = true;
    showTardisConsolePanel(true);
    controls.object.position.set(0, 1.68, -58);
    camera.lookAt(0, 3.2, -82);
    statusEl.textContent = `Inside the persistent TARDIS control room. Use a notebook-world button or Talk command, or exit back to ${returnAreaLabel()}.`;
    return;
  }
  addPlane("TARDIS exterior review floor", 28, 28, new THREE.Vector3(0, 0, 0), new THREE.MeshStandardMaterial({ color: 0x1a2430, roughness: 0.82 }));
  buildPoliceBoxExterior();
  controls.object.position.set(0, 1.68, 8);
  camera.lookAt(0, 2.1, 0);
  statusEl.textContent = "Outside the TARDIS. Press E at the police-box doors to open them, then walk through the doorway and press E.";
}

function addVosgesFacadeSide(name, x, z, width, yaw) {
  const brick = new THREE.MeshStandardMaterial({ color: 0x8f513f, roughness: 0.9 });
  const stoneTrim = new THREE.MeshStandardMaterial({ color: 0xd8c8aa, roughness: 0.88 });
  const slate = new THREE.MeshStandardMaterial({ color: 0x25313d, roughness: 0.72 });
  addBoxYaw(`${name} red brick facade seed`, new THREE.Vector3(width, 13, 1.2), new THREE.Vector3(x, 6.5, z), brick, yaw);
  addBoxYaw(`${name} pale stone arcade band seed`, new THREE.Vector3(width, 3.2, 1.35), new THREE.Vector3(x, 1.8, z + (yaw === 0 ? 0.18 : 0)), stoneTrim, yaw);
  addBoxYaw(`${name} slate mansard roof seed`, new THREE.Vector3(width + 1.5, 3.4, 4.5), new THREE.Vector3(x, 14.6, z), slate, yaw);
  const count = Math.max(5, Math.floor(width / 9));
  for (let i = 0; i < count; i++) {
    const offset = -width / 2 + (i + 0.5) * (width / count);
    const px = yaw === 0 ? x + offset : x;
    const pz = yaw === 0 ? z + 0.82 : z + offset;
    addBoxYaw(`${name} arcade opening shadow seed`, new THREE.Vector3(3.6, 2.5, 0.18), new THREE.Vector3(px, 1.55, pz), materials.sign, yaw);
    for (const y of [6.0, 9.6]) {
      addBoxYaw(`${name} tall window glass seed`, new THREE.Vector3(2.2, 2.7, 0.16), new THREE.Vector3(px, y, pz), materials.glass, yaw);
      addBoxYaw(`${name} pale stone window frame seed`, new THREE.Vector3(2.65, 3.1, 0.12), new THREE.Vector3(px, y, pz - (yaw === 0 ? 0.05 : 0)), stoneTrim, yaw);
    }
    addBoxYaw(`${name} dormer seed`, new THREE.Vector3(1.8, 1.7, 0.8), new THREE.Vector3(px, 16.4, pz), stoneTrim, yaw);
  }
}

function addVosgesTree(x, z, scale = 1) {
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x6d4b32, roughness: 0.86 });
  const leafMat = new THREE.MeshStandardMaterial({ color: 0x4b7c45, roughness: 0.78 });
  addCylinder("Place des Vosges clipped tree trunk seed", 0.22 * scale, 2.2 * scale, new THREE.Vector3(x, 1.1 * scale, z), trunkMat, 10);
  addSphere("Place des Vosges clipped tree crown seed", 1.45 * scale, new THREE.Vector3(x, 2.65 * scale, z), leafMat, 14, 10);
}

function buildPlaceDesVosgesPreview() {
  resetSceneForStandaloneWorld(0xd8dde0);
  currentArea = "vosges";
  addPlane("Place des Vosges cobbled perimeter seed", 175, 175, new THREE.Vector3(0, 0, 0), materials.cobble);
  addPlane("Square Louis XIII garden lawn seed", 106, 106, new THREE.Vector3(0, 0.035, 0), new THREE.MeshStandardMaterial({ color: 0x6c8f55, roughness: 0.95 }));
  const pathMat = new THREE.MeshStandardMaterial({ color: 0xd6c89f, roughness: 0.92 });
  addBox("Square Louis XIII east west path seed", new THREE.Vector3(104, 0.035, 4.2), new THREE.Vector3(0, 0.06, 0), pathMat);
  addBox("Square Louis XIII north south path seed", new THREE.Vector3(4.2, 0.035, 104), new THREE.Vector3(0, 0.061, 0), pathMat);
  addBoxYaw("Square Louis XIII diagonal path seed", new THREE.Vector3(4.0, 0.035, 130), new THREE.Vector3(0, 0.062, 0), pathMat, Math.PI / 4);
  addBoxYaw("Square Louis XIII diagonal path seed", new THREE.Vector3(4.0, 0.035, 130), new THREE.Vector3(0, 0.063, 0), pathMat, -Math.PI / 4);
  addGrassBladeField({
    name: "Square Louis XIII individual grass blades",
    x: 0,
    z: 0,
    width: 102,
    depth: 102,
    count: 16000,
    seed: 61701,
    avoid: [
      { x: 0, z: 0, sx: 108, sz: 6.4 },
      { x: 0, z: 0, sx: 6.4, sz: 108 },
      { x: 0, z: 0, sx: 6.3, sz: 134, yaw: Math.PI / 4 },
      { x: 0, z: 0, sx: 6.3, sz: 134, yaw: -Math.PI / 4 },
      { x: 0, z: 0, sx: 9, sz: 9 },
      { x: -28, z: -28, sx: 8, sz: 8 },
      { x: 28, z: -28, sx: 8, sz: 8 },
      { x: -28, z: 28, sx: 8, sz: 8 },
      { x: 28, z: 28, sx: 8, sz: 8 },
    ],
  });
  addCylinder("Louis XIII statue plinth placeholder", 2.2, 0.55, new THREE.Vector3(0, 0.28, 0), materials.stoneDark, 28);
  addCylinder("Louis XIII equestrian statue placeholder", 0.6, 2.6, new THREE.Vector3(0, 1.65, 0), materials.darkMetal, 12);
  const fountainMat = new THREE.MeshPhysicalMaterial({ color: 0x739aaa, transparent: true, opacity: 0.55, roughness: 0.08 });
  for (const [x, z] of [[-28, -28], [28, -28], [-28, 28], [28, 28]]) {
    addCylinder("Place des Vosges fountain basin seed", 3.0, 0.22, new THREE.Vector3(x, 0.12, z), materials.stoneDark, 36);
    addCylinder("Place des Vosges fountain water seed", 2.6, 0.08, new THREE.Vector3(x, 0.3, z), fountainMat, 36);
    addCylinder("Place des Vosges fountain jet seed", 0.05, 2.0, new THREE.Vector3(x, 1.2, z), new THREE.MeshBasicMaterial({ color: 0xdff8ff, transparent: true, opacity: 0.55 }), 8);
  }
  for (let p = -46; p <= 46; p += 11.5) {
    addVosgesTree(p, -50, 0.95);
    addVosgesTree(p, 50, 0.95);
    addVosgesTree(-50, p, 0.95);
    addVosgesTree(50, p, 0.95);
  }
  const fenceMat = new THREE.MeshStandardMaterial({ color: 0x303535, roughness: 0.46, metalness: 0.35 });
  for (let p = -56; p <= 56; p += 4) {
    addCylinder("Place des Vosges garden fence post seed", 0.05, 1.1, new THREE.Vector3(p, 0.55, -56), fenceMat, 8);
    addCylinder("Place des Vosges garden fence post seed", 0.05, 1.1, new THREE.Vector3(p, 0.55, 56), fenceMat, 8);
    addCylinder("Place des Vosges garden fence post seed", 0.05, 1.1, new THREE.Vector3(-56, 0.55, p), fenceMat, 8);
    addCylinder("Place des Vosges garden fence post seed", 0.05, 1.1, new THREE.Vector3(56, 0.55, p), fenceMat, 8);
  }
  addVosgesFacadeSide("north Place des Vosges arcade", 0, -78, 150, 0);
  addVosgesFacadeSide("south Place des Vosges arcade", 0, 78, 150, Math.PI);
  addVosgesFacadeSide("east Place des Vosges arcade", 78, 0, 150, Math.PI / 2);
  addVosgesFacadeSide("west Place des Vosges arcade", -78, 0, 150, -Math.PI / 2);
  if (parisTardisArrived) buildPoliceBoxExterior(new THREE.Vector3(63, 0, 66));
  placeLabel("Place des Vosges seed: 140m-class square, Square Louis XIII garden, four fountains, arcades, and red-brick/pale-stone facades. Blueprint first; details remain source-labeled.", new THREE.Vector3(-42, 3.2, 61), 0.45, 16, 2.3, 36);
  controls.object.position.set(58, 1.68, 58);
  camera.lookAt(0, 2.5, 0);
  statusEl.textContent = "Place des Vosges seed loaded. C calls the TARDIS. E enters it from the police-box doors.";
}

function enterTardisInterior() {
  if (!tardisState.consoleScreen) {
    resetSceneForTardisPreview();
    scene.add(new THREE.HemisphereLight(0x89c7ff, 0x02060a, 1.2));
    const key = new THREE.DirectionalLight(0xb9dfff, 2.2);
    key.position.set(-8, 12, 12);
    scene.add(key);
    buildTardisInterior();
  }
  tardisState.inside = true;
  showTardisConsolePanel(true);
  controls.object.position.set(0, 1.68, -58);
  camera.lookAt(0, 3.2, -82);
  statusEl.textContent = `Inside the persistent TARDIS control room. Use a notebook-world button or Talk command, or exit back to ${returnAreaLabel()}.`;
}

function exitTardisInterior() {
  releaseTardisUse();
  showTardisConsolePanel(false);
  const returnArea = safeReturnArea();
  if (requestedArea === "tardis" && requestedView === "interior") {
    if (returnArea === "home" || returnArea === "library") {
      requestShellLocation(returnArea, { arrival: "tardis" });
      return;
    }
    location.href = `${location.pathname}?area=${returnArea}&arrival=tardis`;
    return;
  }
  tardisState.inside = false;
  controls.object.position.set(0, 1.68, 6.4);
  camera.lookAt(0, 2.0, 0);
  statusEl.textContent = "Outside the TARDIS. It is still the same persistent interior behind the door.";
}

function openPersistentTardisInterior() {
  if (!requestTardisUse()) return;
  const returnArea = currentArea === "vosges" ? "vosges" : "louvre";
  location.href = `${location.pathname}?area=tardis&view=interior&return=${returnArea}&caller=${encodeURIComponent(tardisCallerId)}`;
}

function handleTardisUse() {
  const obj = controls.object;
  if (!tardisState.inside) {
    const group = tardisState.exteriorGroup;
    const gx = group?.position.x || 0;
    const gz = group?.position.z || 0;
    const local = new THREE.Vector3(obj.position.x - gx, 0, obj.position.z - gz)
      .applyAxisAngle(new THREE.Vector3(0, 1, 0), -(group?.rotation.y || 0));
    if (Math.abs(local.x) < 1.35 && local.z > 0.55 && local.z < 2.35) {
      if (!tardisState.doorOpen) {
        setTardisExteriorDoorOpen(true);
        statusEl.textContent = "The TARDIS doors open. The console is visible inside; walk through the doorway and press E.";
        return;
      }
      if (local.z < 1.05) {
        statusEl.textContent = "The TARDIS interior is visible. Step through the open doorway first.";
        return;
      }
      if (requestedArea === "tardis") enterTardisInterior();
      else openPersistentTardisInterior();
    } else {
      statusEl.textContent = "Walk to the police-box doors, then press E to enter manually.";
    }
    return;
  }
  if (obj.position.z > -62) {
    exitTardisInterior();
  } else {
    statusEl.textContent = "Walk back toward the interior exit side, then press E.";
  }
}

function callTardisToUser() {
  if (tardisState.inside) {
    statusEl.textContent = "You are already inside the TARDIS. Finish travel before answering another call.";
    return;
  }
  const active = getTardisUseRecord();
  if (active && active.user !== tardisCallerId) {
    requestTardisUse();
    return;
  }
  const obj = controls.object;
  const forward = new THREE.Vector3();
  camera.getWorldDirection(forward);
  forward.y = 0;
  if (forward.lengthSq() < 0.001) forward.set(0, 0, -1);
  forward.normalize();
  const spawn = new THREE.Vector3(obj.position.x + forward.x * 5.2, 0, obj.position.z + forward.z * 5.2);
  if (!tardisState.exteriorGroup) {
    buildPoliceBoxExterior(spawn);
  } else {
    tardisState.exteriorGroup.position.copy(spawn);
  }
  const toPlayer = new THREE.Vector3(obj.position.x - spawn.x, 0, obj.position.z - spawn.z);
  tardisState.exteriorGroup.rotation.y = Math.atan2(toPlayer.x, toPlayer.z);
  setTardisExteriorDoorOpen(false);
  statusEl.textContent = "TARDIS call accepted. Walk to the front doors, press E to open them, then walk through and press E.";
}

function cycleTardisDestination() {
  selectTardisDestination((tardisState.selectedDestination + 1) % tardisDestinations.length);
}

function travelToDestination(destination) {
  if (!destination.travelReady) {
    statusEl.textContent = `${destination.title} is ${destination.status}. ${destination.source}.`;
    return;
  }
  if (destination.ownerReviewOnly && tardisCallerId !== destination.allowedCaller) {
    statusEl.textContent = `${destination.title} is an owner-only solo review route. It did not activate or transport a person.`;
    return;
  }
  releaseTardisUse();
  showTardisConsolePanel(false);
  const shellLocation = destination.shellLocation || destination.area;
  if (window.parent && window.parent !== window) {
    requestShellLocation(shellLocation, {
      arrival: "tardis",
      returnLocation: shellLocation,
      soloReview: Boolean(destination.ownerReviewOnly),
      bookmark: destination.soloQuery?.bookmark || "",
    });
    return;
  }
  if (destination.ownerReviewOnly) {
    const query = new URLSearchParams({ area: destination.area, ...destination.soloQuery });
    location.href = `${location.pathname}?${query}`;
    return;
  }
  location.href = `${location.pathname}?area=${destination.area}&arrival=tardis`;
}

function travelToSelectedDestination() {
  travelToDestination(selectedTardisDestination());
}

window.kiraTardisConsole = {
  notebookWorlds: tardisNotebookWorlds,
  destinations: tardisDestinations,
  selected() {
    return selectedTardisDestination();
  },
  parkedExit() {
    return safeReturnArea();
  },
  select(index) {
    selectTardisDestination(index);
    return selectedTardisDestination();
  },
  selectWorld(index) {
    selectTardisNotebookWorld(index);
    return selectedTardisNotebookWorld();
  },
  selectArea(index) {
    selectTardisNotebookArea(index, { travel: false });
    return selectedTardisDestination();
  },
  talk(command) {
    return handleTardisCommand(command);
  },
  requests() {
    try {
      return JSON.parse(localStorage.getItem("kira_tardis_talk_requests") || "[]");
    } catch {
      return [];
    }
  },
  preview() {
    previewSelectedDestination();
    return selectedTardisDestination();
  },
  travel() {
    travelToSelectedDestination();
    return selectedTardisDestination();
  },
  exit() {
    exitTardisInterior();
    return { parkedExit: safeReturnArea() };
  },
};

if (requestedArea === "louvre" && parisTardisArrived) {
  buildPoliceBoxExterior(new THREE.Vector3(72, 0, 54));
} else if (requestedArea === "tardis") {
  buildTardisGatewayPreview();
} else if (requestedArea === "vosges") {
  buildPlaceDesVosgesPreview();
}

function saveVisitSnapshot() {
  renderer.render(scene, camera);
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const link = document.createElement("a");
  link.download = `louvre_visit_${stamp}.png`;
  link.href = renderer.domElement.toDataURL("image/png");
  link.click();
  statusEl.textContent = "Snapshot saved by the browser.";
}

const keys = new Set();
addEventListener("keydown", (event) => {
  if (event.code === "KeyP") {
    saveVisitSnapshot();
    return;
  }
  if (soloLouvreMode && event.code === "KeyF") {
    setFeedbackOpen(feedbackPanelEl?.hidden !== false);
    return;
  }
  if (soloLouvreMode && event.code === "KeyR") {
    cycleReviewRoute();
    return;
  }
  if (soloLouvreMode && event.code === "KeyB") {
    cycleReviewBookmark();
    return;
  }
  if (soloLouvreMode && event.code === "KeyL") {
    setTruthMarkersVisible(!truthMarkersVisible);
    statusEl.textContent = `In-world truth markers ${truthMarkersVisible ? "shown" : "hidden"}.`;
    return;
  }
  if (soloLouvreMode && event.code === "KeyE") {
    const nearApproximateEntrance = Math.abs(controls.object.position.x) < 5.2 && controls.object.position.z > 12 && controls.object.position.z < 24;
    if (nearApproximateEntrance) void toggleApproximateEntrance();
    else statusEl.textContent = "E operates only the bounded approximate Pyramid entrance when you are near its threshold. Exact/full interior routes stay locked.";
    return;
  }
  if (soloLouvreMode && event.code === "KeyC") {
    statusEl.textContent = "Solo review isolation is active. This preview does not call or load the TARDIS, a person, a mind, or voice.";
    return;
  }
  if (event.code === "KeyE" && (requestedArea === "tardis" || requestedArea === "louvre" || requestedArea === "vosges")) {
    handleTardisUse();
    return;
  }
  if (event.code === "KeyC" && (requestedArea === "tardis" || requestedArea === "louvre" || requestedArea === "vosges")) {
    callTardisToUser();
    return;
  }
  if (requestedArea === "tardis" && event.code === "KeyT") {
    cycleTardisDestination();
    return;
  }
  if (requestedArea === "tardis" && event.code === "Enter") {
    travelToSelectedDestination();
    return;
  }
  if (event.code === "KeyM") {
    statusEl.textContent = "Only the bounded approximate entrance and spiral-descent owner-review slice is available. Full Louvre interiors, elevators, galleries, rooms, and artwork remain locked.";
    return;
  }
  keys.add(event.code);
});
addEventListener("keyup", (event) => keys.delete(event.code));

const direction = new THREE.Vector3();
const clock = new THREE.Clock();

function moveToArea(area) {
  currentArea = area;
  travelCooldown = 0.9;
  const obj = controls.object;
  obj.position.set(52, 1.68, 66);
  camera.lookAt(20, 6, 0);
  statusEl.textContent = "Returned to the Louvre courtyard. Interior travel is blueprint-locked.";
}

function updateAreaTravel(obj) {
  return;
}

function updateInteractivePieces(obj) {
  return;
}

function pushOutsideRect(obj, centerX, centerZ, halfX, halfZ, message, collisionId = null) {
  const dx = obj.position.x - centerX;
  const dz = obj.position.z - centerZ;
  if (Math.abs(dx) >= halfX || Math.abs(dz) >= halfZ) return false;
  const pushX = halfX - Math.abs(dx);
  const pushZ = halfZ - Math.abs(dz);
  if (pushX < pushZ) {
    obj.position.x = centerX + Math.sign(dx || 1) * halfX;
  } else {
    obj.position.z = centerZ + Math.sign(dz || 1) * halfZ;
  }
  statusEl.textContent = message;
  if (collisionId) recordReviewCollision(collisionId, message);
  return true;
}

function pushOutsideCircle(obj, centerX, centerZ, radius, message) {
  const dx = obj.position.x - centerX;
  const dz = obj.position.z - centerZ;
  const distance = Math.hypot(dx, dz);
  if (distance >= radius) return false;
  const scale = radius / Math.max(distance, 0.001);
  obj.position.x = centerX + dx * scale;
  obj.position.z = centerZ + dz * scale;
  statusEl.textContent = message;
  return true;
}

function keepOutsideCourtyardObstacles(obj) {
  const atPyramidEntranceApron = Math.abs(obj.position.x) < 4.8 && obj.position.z >= 17.25 && obj.position.z < 23.5;
  if (atPyramidEntranceApron) {
    statusEl.textContent = "At the approximate entrance apron. Press E to stage the bounded destination cells and operate the functional review doors; their real dimensions/mechanism are unknown.";
    return;
  }
  const crossingEntranceDoor = Math.abs(obj.position.x) < 4.8 && obj.position.z > 15.8 && obj.position.z < 17.25;
  if (crossingEntranceDoor) {
    obj.position.z = 17.25;
    const message = "The approximate entrance threshold is solid until its door is open and the bounded destination cells are collision-ready.";
    statusEl.textContent = message;
    recordReviewCollision("approximate_entrance_threshold", message);
    return;
  }
  for (const collider of louvreContract.colliders) {
    if (pushOutsideRect(
      obj,
      collider.center[0],
      collider.center[1],
      collider.half_extents[0] + avatarClearanceRadius,
      collider.half_extents[1] + avatarClearanceRadius,
      collider.message,
      collider.id,
    )) return;
  }
}

function keepInsideTardisBounds(obj) {
  if (!tardisState.inside) {
    obj.position.x = THREE.MathUtils.clamp(obj.position.x, -12, 12);
    obj.position.z = THREE.MathUtils.clamp(obj.position.z, -12, 12);
    keepOutsideTardisExterior(obj);
    return;
  }
  const centerZ = -82;
  const dx = obj.position.x;
  const dz = obj.position.z - centerZ;
  const radius = Math.hypot(dx, dz);
  if (radius > 25.5) {
    const scale = 25.5 / radius;
    obj.position.x = dx * scale;
    obj.position.z = centerZ + dz * scale;
    statusEl.textContent = "The TARDIS interior wall blocks this route.";
  }
  pushOutsideCircle(obj, 0, centerZ, 5.2, "The central console blocks this route.");
}

function keepOutsideTardisExterior(obj) {
  if (!tardisState.exteriorGroup) return;
  const gx = tardisState.exteriorGroup.position.x;
  const gz = tardisState.exteriorGroup.position.z;
  const local = new THREE.Vector3(obj.position.x - gx, 0, obj.position.z - gz)
    .applyAxisAngle(new THREE.Vector3(0, 1, 0), -tardisState.exteriorGroup.rotation.y);
  const atDoor = tardisState.doorOpen && Math.abs(local.x) < 1.2 && local.z > 0.9 && local.z < 2.25;
  if (!atDoor) {
    pushOutsideRect(obj, gx, gz, 1.08, 1.08, "The TARDIS exterior is solid. Use the front doors manually with E.");
  }
}

function updateMovement(delta) {
  travelCooldown = Math.max(0, travelCooldown - delta);
  direction.z = Number(keys.has("KeyW")) - Number(keys.has("KeyS"));
  direction.x = Number(keys.has("KeyD")) - Number(keys.has("KeyA"));
  direction.normalize();
  const speed = keys.has("ShiftLeft") || keys.has("ShiftRight")
    ? louvreContract.scale.fast_review_speed_mps
    : louvreContract.scale.walking_speed_mps;
  if (controls.isLocked) {
    const previousPosition = controls.object.position.clone();
    const beforeX = controls.object.position.x;
    const beforeZ = controls.object.position.z;
    if (direction.z !== 0) controls.moveForward(direction.z * speed * delta);
    if (direction.x !== 0) controls.moveRight(direction.x * speed * delta);
    const obj = controls.object;
    if (requestedArea === "tardis") {
      obj.position.y = louvreContract.scale.eye_height_m;
      keepInsideTardisBounds(obj);
    } else if (requestedArea === "vosges") {
      obj.position.y = louvreContract.scale.eye_height_m;
      obj.position.x = THREE.MathUtils.clamp(obj.position.x, -84, 84);
      obj.position.z = THREE.MathUtils.clamp(obj.position.z, -84, 84);
      keepOutsideTardisExterior(obj);
    } else {
      const unclampedX = obj.position.x;
      const unclampedZ = obj.position.z;
      obj.position.x = THREE.MathUtils.clamp(obj.position.x, -108, 108);
      obj.position.z = THREE.MathUtils.clamp(obj.position.z, -84, 84);
      if (obj.position.x !== unclampedX || obj.position.z !== unclampedZ) {
        recordReviewCollision("review_boundary", "The solo exterior review boundary blocks further travel.");
      }
      const surfaceAccepted = soloLouvreMode
        ? applyApproximateLouvreSurface(obj, previousPosition)
        : true;
      if (!soloLouvreMode) obj.position.y = louvreContract.scale.eye_height_m;
      if (surfaceAccepted && (!soloLouvreMode || louvreReviewRuntime.lastSurface.kind === "exterior")) keepOutsideCourtyardObstacles(obj);
      keepOutsideTardisExterior(obj);
      if (soloLouvreMode) void requestLouvreStreamingForPosition(obj.position);
    }
    const actualDistance = Math.hypot(obj.position.x - beforeX, obj.position.z - beforeZ);
    const maximumExpectedStep = speed * delta * 2 + 0.05;
    if ((direction.x !== 0 || direction.z !== 0) && actualDistance <= maximumExpectedStep) {
      reviewSessionMetrics.distance_walked_m += actualDistance;
    }
    updateInteractivePieces(obj);
    updateAreaTravel(obj);
    updateNearestLandmark();
    updateReviewMetricDisplay();
  }
}

function faceLabels() {
  for (const child of scene.children) {
    if (!child.userData?.isLabel) continue;
    child.lookAt(camera.position.x, child.position.y, camera.position.z);
  }
}

function applyReviewCamera() {
  if (soloLouvreMode) {
    const bookmarkId = louvreContract.review_bookmarks.some((bookmark) => bookmark.id === requestedBookmarkId)
      ? requestedBookmarkId
      : louvreContract.review_bookmarks[0].id;
    setReviewBookmark(bookmarkId, { updateUrl: false });
  } else if (requestedArea === "tardis" && requestedView === "interior") {
    tardisState.inside = true;
    controls.object.position.set(0, 1.68, -58);
    camera.position.set(0, 2.0, -62);
    camera.lookAt(0, 3.5, -82);
  } else if (requestedArea === "tardis" && requestedView === "exterior") {
    tardisState.inside = false;
    camera.position.set(0, 1.9, 8);
    camera.lookAt(0, 2.4, 0);
  } else if (requestedArea === "vosges" && requestedView === "overview") {
    camera.position.set(0, 46, 92);
    camera.lookAt(0, 1.8, 0);
  } else if (requestedView === "courtyard") {
    camera.position.set(0, 4.2, 66);
    camera.lookAt(0, 7.0, 3);
  } else if (requestedView === "entrance") {
    camera.position.set(0, 1.68, 34);
    camera.lookAt(0, 2.2, 18.5);
  } else if (requestedView === "facade") {
    camera.position.set(-58, 3.2, 48);
    camera.lookAt(-18, 11, -74);
  }
}

function resize() {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
}
addEventListener("resize", resize);

function animate() {
  const delta = Math.min(clock.getDelta(), 0.04);
  if (soloLouvreMode) updateApproximateEntrance(delta);
  updateMovement(delta);
  faceLabels();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

if (soloLouvreMode) registerLouvreReviewCells();
loadActorManifest();
applyReviewCamera();
if (requestedArea === "tardis") {
  statusEl.textContent = requestedView === "interior"
    ? `Inside the persistent TARDIS control room. Use a notebook-world button or Talk command, or exit back to ${returnAreaLabel()}.`
    : "TARDIS gateway preview. E opens and enters; inside, notebook-world buttons and Talk choose destinations.";
} else if (requestedArea === "vosges") {
  statusEl.textContent = "Place des Vosges seed. Click to walk. C calls the TARDIS, E enters at the police-box doors, P saves a snapshot.";
} else {
  statusEl.textContent = soloLouvreMode
    ? photoModeDefault
      ? "Solo photo mode. The bounded approximate circulation slice may stream; no actors, minds, voices, TARDIS, Home World, elevators, galleries, or artwork can load."
      : "Solo owner review ready. E operates the approximate entrance near its threshold; the spiral descent is walkable, the escalator forms are visible-only, and exact/full interior areas stay locked."
    : photoModeDefault
      ? "Photo mode. Actors are hidden unless ?actors=1 is enabled."
      : "Ready. Click to walk. Pyramid glass blocks movement outside the bounded approximate circulation review path. Press P for snapshot.";
}

updateNearestLandmark();
if (soloLouvreMode && activeReviewRouteIndex < 0) setReviewRoute(0);
updateReviewMetricDisplay(true);
const initialRouteChecks = runStaticRouteChecks();
window.__louvreNotebookDebug = {
  worldId: louvreContract.world_id,
  locationId: louvreContract.location_id,
  buildId: louvreContract.build_id,
  status: louvreContract.status,
  streaming: louvreCellStreaming.snapshot([[camera.position.x, camera.position.y, camera.position.z]]),
  soloReviewOnly: soloLouvreMode,
  temporaryAiActivationAllowed: false,
  peopleLoaded: 0,
  mindsLoaded: 0,
  voiceLoaded: false,
  ollamaLoaded: false,
  homeWorldLoaded: false,
  homeWorldMutationAllowed: false,
  stripMallMutationAllowed: false,
  runtimeRegistered: false,
  interiorEnabled: false,
  boundedApproximateCirculationOwnerReviewEnabled: soloLouvreMode,
  fullLouvreInteriorEnabled: false,
  elevatorsEnabled: false,
  galleryEnabled: false,
  artworkEnabled: false,
  eyeHeightM: louvreContract.scale.eye_height_m,
  avatarClearanceRadiusM: avatarClearanceRadius,
  colliderCount: louvreContract.colliders.length,
  routeCount: louvreContract.routes.length,
  landmarkCount: louvreContract.landmarks.length,
  bookmarkCount: louvreContract.review_bookmarks.length,
  truthMarkerCount: truthMarkerMeshes.length,
  smallerPyramidCount: 2,
  initialRouteChecks,
  contract: louvreContract,
  blocked(x, z, clearance = avatarClearanceRadius) {
    return Boolean(collisionAt(x, z, clearance));
  },
  collisionProbe(x, z, clearance = avatarClearanceRadius) {
    return collisionAt(x, z, clearance);
  },
  runStaticRouteChecks,
  measureRouteAt,
  setWalkPosition,
  attemptWalkPosition(x, z) {
    return setWalkPosition(x, z, { recordRejected: true });
  },
  setRoute: setReviewRoute,
  cycleRoute: cycleReviewRoute,
  setBookmark: setReviewBookmark,
  cycleBookmark: cycleReviewBookmark,
  setTruthMarkersVisible,
  requestStreamingAt(x, y, z) {
    return requestLouvreStreamingForPosition(new THREE.Vector3(x, y, z), true);
  },
  waitForStreamingIdle() {
    return louvreReviewRuntime.streamingPromise;
  },
  streamingSnapshot() {
    return louvreCellStreaming.snapshot(louvreStreamingPosition());
  },
  async setApproximateEntranceOpen(open) {
    return setApproximateEntranceDoorTarget(Boolean(open));
  },
  entranceSnapshot() {
    const entrance = currentEntranceCell();
    return entrance ? {
      loaded: true,
      phase: entrance.state.phase,
      progress: Number(entrance.state.door_progress.toFixed(4)),
      target: entrance.state.door_target,
      threshold_collision_solid: entrance.state.threshold_collision_solid,
      threshold_passable: entranceThresholdPassable(),
      operation_count: entrance.state.operation_count,
    } : { loaded: false, phase: "unloaded", progress: 0, target: 0, threshold_collision_solid: true, threshold_passable: false, operation_count: 0 };
  },
  async waitForEntrancePhase(phase, timeoutMs = 4000) {
    const started = performance.now();
    while (performance.now() - started < timeoutMs) {
      if (currentEntranceCell()?.state.phase === phase) return true;
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    return false;
  },
  attemptApproximateThresholdCrossing() {
    const obj = controls.object;
    const previous = new THREE.Vector3(0, louvreContract.scale.eye_height_m, 17.6);
    obj.position.set(0, louvreContract.scale.eye_height_m, 17.05);
    louvreReviewRuntime.lastSurface = { floor_y_m: 0, cell_id: "cour_napoleon_exterior", kind: "exterior" };
    const accepted = applyApproximateLouvreSurface(obj, previous);
    return { accepted, position_m: obj.position.toArray().map((value) => Number(value.toFixed(4))), surface: { ...louvreReviewRuntime.lastSurface } };
  },
  walkApproximateSpiral(direction = "down", samples = 32) {
    const obj = controls.object;
    const values = Array.from({ length: Math.max(3, samples) }, (_, index) => index / (Math.max(3, samples) - 1));
    if (direction === "up") values.reverse();
    const results = [];
    let previous = obj.position.clone();
    for (const progress of values) {
      const angle = THREE.MathUtils.lerp(APPROXIMATE_SPIRAL.start_angle_rad, APPROXIMATE_SPIRAL.end_angle_rad, progress);
      obj.position.x = APPROXIMATE_SPIRAL.center_x + Math.sin(angle) * APPROXIMATE_SPIRAL.radius_m;
      obj.position.z = APPROXIMATE_SPIRAL.center_z + Math.cos(angle) * APPROXIMATE_SPIRAL.radius_m;
      const accepted = applyApproximateLouvreSurface(obj, previous);
      results.push({ accepted, progress: Number(progress.toFixed(4)), floor_y_m: Number((obj.position.y - louvreContract.scale.eye_height_m).toFixed(4)) });
      previous = obj.position.clone();
    }
    return results;
  },
  escalatorSurfaceProbe() {
    return resolveApproximateLouvreSurface(6.5, 1.2, -8);
  },
  setCirculationReviewView(view = "stair") {
    controls.unlock();
    if (view === "lower") {
      camera.position.set(-12, -6.32, 8.5);
      camera.lookAt(0, -5.2, 5.5);
    } else if (view === "entrance") {
      camera.position.set(0, 1.68, 22.5);
      camera.lookAt(0, 1.2, 16.5);
    } else {
      camera.position.set(10, 2, 18);
      camera.lookAt(0, -4, 8);
    }
    return camera.position.toArray().map((value) => Number(value.toFixed(3)));
  },
  setCirculationReviewCamera(position, target) {
    if (!Array.isArray(position) || position.length !== 3 || !position.every(Number.isFinite)) return false;
    if (!Array.isArray(target) || target.length !== 3 || !target.every(Number.isFinite)) return false;
    controls.unlock();
    camera.position.set(...position);
    camera.lookAt(...target);
    return true;
  },
  runtimeObjectCounts() {
    let elevator = 0;
    let gallery = 0;
    let artwork = 0;
    let escalator = 0;
    scene.traverse((object) => {
      const kind = object.userData?.louvre_runtime_kind || "";
      if (kind === "elevator") elevator += 1;
      if (kind === "gallery") gallery += 1;
      if (kind === "artwork") artwork += 1;
      if (kind === "visible_only_escalator_blockout") escalator += 1;
    });
    return { elevator, gallery, artwork, escalator };
  },
  rendererMetrics() {
    return {
      triangles: renderer.info.render.triangles,
      draw_calls: renderer.info.render.calls,
      geometries: renderer.info.memory.geometries,
      textures: renderer.info.memory.textures,
    };
  },
  async streamingFailureProbes() {
    const cloneContract = () => JSON.parse(JSON.stringify(louvreStreamingContract));
    const normalMetrics = {
      cour_napoleon_exterior: { asset_bytes: 6291456, triangles: 80000, texture_bytes: 3145728, draw_calls: 500 },
      pyramid_entrance_transition: { asset_bytes: 196608, triangles: 256, texture_bytes: 0, draw_calls: 6 },
      under_pyramid_level_minus_2_circulation: { asset_bytes: 1048576, triangles: 9000, texture_bytes: 0, draw_calls: 105 },
    };
    const registerNoop = (runtime, id, metrics, counters, { commitFails = false, preflightFails = false } = {}) => runtime.registerCell(id, {
      async load() {
        counters.loaded += 1;
        return { ready: true, collision_ready: true, metrics };
      },
      async commit() {
        if (commitFails) throw new Error("intentional owner-review commit probe");
      },
      async preflightUnload() {
        if (preflightFails) throw new Error("intentional owner-review unload preflight probe");
      },
      async unload() {
        counters.disposed += 1;
      },
    });

    const missingCounters = { loaded: 0, disposed: 0 };
    const missingRuntime = createLouvreCellStreamingScaffold(cloneContract());
    registerNoop(missingRuntime, "cour_napoleon_exterior", normalMetrics.cour_napoleon_exterior, missingCounters);
    await missingRuntime.apply([[0, 1.68, 62]]);
    missingRuntime.authorizeCell("under_pyramid_level_minus_2_circulation");
    const missing = await missingRuntime.apply([[0, 1.68, 17]]);

    const budgetCounters = { loaded: 0, disposed: 0 };
    const budgetRuntime = createLouvreCellStreamingScaffold(cloneContract());
    registerNoop(budgetRuntime, "cour_napoleon_exterior", normalMetrics.cour_napoleon_exterior, budgetCounters);
    registerNoop(budgetRuntime, "pyramid_entrance_transition", { ...normalMetrics.pyramid_entrance_transition, triangles: 999999 }, budgetCounters);
    registerNoop(budgetRuntime, "under_pyramid_level_minus_2_circulation", normalMetrics.under_pyramid_level_minus_2_circulation, budgetCounters);
    await budgetRuntime.apply([[0, 1.68, 62]]);
    budgetRuntime.authorizeCell("under_pyramid_level_minus_2_circulation");
    const budget = await budgetRuntime.apply([[0, 1.68, 17]]);

    const commitCounters = { loaded: 0, disposed: 0 };
    const commitRuntime = createLouvreCellStreamingScaffold(cloneContract());
    registerNoop(commitRuntime, "cour_napoleon_exterior", normalMetrics.cour_napoleon_exterior, commitCounters);
    registerNoop(commitRuntime, "pyramid_entrance_transition", normalMetrics.pyramid_entrance_transition, commitCounters, { commitFails: true });
    registerNoop(commitRuntime, "under_pyramid_level_minus_2_circulation", normalMetrics.under_pyramid_level_minus_2_circulation, commitCounters);
    await commitRuntime.apply([[0, 1.68, 62]]);
    commitRuntime.authorizeCell("under_pyramid_level_minus_2_circulation");
    const commit = await commitRuntime.apply([[0, 1.68, 17]]);

    const unloadCounters = { loaded: 0, disposed: 0 };
    const unloadRuntime = createLouvreCellStreamingScaffold(cloneContract());
    registerNoop(unloadRuntime, "cour_napoleon_exterior", normalMetrics.cour_napoleon_exterior, unloadCounters);
    registerNoop(unloadRuntime, "pyramid_entrance_transition", normalMetrics.pyramid_entrance_transition, unloadCounters, { preflightFails: true });
    registerNoop(unloadRuntime, "under_pyramid_level_minus_2_circulation", normalMetrics.under_pyramid_level_minus_2_circulation, unloadCounters);
    await unloadRuntime.apply([[0, 1.68, 62]]);
    unloadRuntime.authorizeCell("under_pyramid_level_minus_2_circulation");
    await unloadRuntime.apply([[0, 1.68, 17]]);
    const unload = await unloadRuntime.apply([[0, 1.68, 84]]);
    return {
      missing_registration: { snapshot: missing, counters: missingCounters },
      budget_overrun: { snapshot: budget, counters: budgetCounters },
      commit_failure: { snapshot: commit, counters: commitCounters },
      unload_preflight_failure: { snapshot: unload, counters: unloadCounters },
    };
  },
  reviewMetrics: reviewMetricsSnapshot,
  buildOwnerReviewPackage,
  feedbackEntries: readReviewFeedback,
  getSnapshot() {
    const position = controls.object.position;
    return {
      position_m: [Number(position.x.toFixed(3)), Number(position.y.toFixed(3)), Number(position.z.toFixed(3))],
      nearest_landmark_id: currentNearestLandmark?.id || null,
      active_route_id: louvreContract.routes[activeReviewRouteIndex]?.id || null,
      active_bookmark_id: currentReviewBookmark()?.id || null,
      reproducible_bookmark_url: currentReviewBookmark() ? reviewBookmarkUrl(currentReviewBookmark().id) : null,
      route_checks: runStaticRouteChecks(),
      measurements: reviewMetricsSnapshot(),
      feedback_count: readReviewFeedback().length,
      actor_manifest_requested: showActors,
      tardis_present: Boolean(tardisState.exteriorGroup),
      truth_markers_visible: truthMarkersVisible,
    };
  },
};
window.__previewReady = false;
Promise.resolve(louvreReviewRuntime.streamingPromise).then((snapshot) => {
  if (snapshot) window.__louvreNotebookDebug.streaming = snapshot;
  window.__previewReady = true;
});
animate();
