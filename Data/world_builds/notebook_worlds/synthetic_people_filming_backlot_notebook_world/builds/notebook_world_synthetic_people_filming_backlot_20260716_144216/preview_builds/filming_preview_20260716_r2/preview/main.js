import * as THREE from "/vendor/three/three.module.js";

const REQUIRED_BUILD_STATUS = "prototype_draft_not_final_not_approved";
const canvas = document.getElementById("world");
const statusNode = document.getElementById("runtime-status");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "low-power" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, 1, 0.05, 400);
const clock = new THREE.Clock();
const keys = new Set();
const routeVisuals = [];
let metadata;
let collision;
let sourceTruth;
let budget;
let buildStatus;
let cameraIndex = 0;
let yaw = 0;
let pitch = -0.12;
let dragging = false;
let lastPointer = null;
let routesVisible = true;

function fail(message, error) {
  statusNode.textContent = message;
  statusNode.classList.add("error");
  window.__previewReady = false;
  window.__previewError = String(error || message);
  console.error(message, error);
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`${url} returned HTTP ${response.status}`);
  }
  return response.json();
}

function color(value) {
  return new THREE.Color(value);
}

function createMaterials(items) {
  const result = new Map();
  for (const item of items) {
    const material = new THREE.MeshStandardMaterial({
      color: color(item.color),
      roughness: item.roughness,
      metalness: item.metalness,
      opacity: item.opacity,
      transparent: item.opacity < 1,
      depthWrite: item.opacity >= 0.8,
    });
    material.name = item.id;
    material.userData.truthLabel = item.truth_label;
    material.userData.sourceNote = item.source_note;
    result.set(item.id, material);
  }
  return result;
}

function createPrimitive(item, materials) {
  let geometry;
  if (item.primitive === "box") {
    geometry = new THREE.BoxGeometry(item.size[0], item.size[1], item.size[2]);
  } else if (item.primitive === "plane") {
    geometry = new THREE.PlaneGeometry(item.size[0], item.size[1]);
  } else if (item.primitive === "cylinder") {
    geometry = new THREE.CylinderGeometry(item.radius, item.radius, item.height, item.segments, 1, false);
  } else {
    throw new Error(`Unsupported primitive ${item.primitive}`);
  }
  const mesh = new THREE.Mesh(geometry, materials.get(item.material_id));
  mesh.name = item.id;
  mesh.position.fromArray(item.position);
  mesh.rotation.set(item.rotation[0], item.rotation[1], item.rotation[2]);
  mesh.userData.category = item.category;
  mesh.userData.truthLabel = item.truth_label;
  mesh.userData.sourceNote = item.source_note;
  mesh.receiveShadow = false;
  mesh.castShadow = false;
  scene.add(mesh);
  return mesh;
}

function createLights(items) {
  for (const item of items) {
    let light;
    if (item.type === "hemisphere") {
      light = new THREE.HemisphereLight(color(item.sky_color), color(item.ground_color), item.intensity);
    } else {
      light = new THREE.DirectionalLight(color(item.color), item.intensity);
      light.position.fromArray(item.position);
    }
    light.name = item.id;
    light.userData.truthLabel = item.truth_label;
    light.userData.sourceNote = item.source_note;
    scene.add(light);
  }
}

function createRoutes(items) {
  for (const [index, item] of items.entries()) {
    const points = item.points.map((point) => new THREE.Vector3(point[0], point[1] + 0.025, point[2]));
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineDashedMaterial({
      color: index % 2 ? 0x6ce0a7 : 0x71c8ff,
      transparent: true,
      opacity: 0.62,
      dashSize: 0.22,
      gapSize: 0.12,
    });
    const line = new THREE.Line(geometry, material);
    line.name = `route_${item.id}`;
    line.userData.routeId = item.id;
    line.computeLineDistances();
    scene.add(line);
    routeVisuals.push(line);
  }
}

function setCameraPreset(index) {
  if (!metadata.cameras.length) return;
  cameraIndex = ((index % metadata.cameras.length) + metadata.cameras.length) % metadata.cameras.length;
  const preset = metadata.cameras[cameraIndex];
  camera.position.fromArray(preset.position);
  camera.fov = preset.fov;
  camera.updateProjectionMatrix();
  const target = new THREE.Vector3().fromArray(preset.target);
  const direction = target.sub(camera.position).normalize();
  yaw = Math.atan2(-direction.x, -direction.z);
  pitch = Math.asin(THREE.MathUtils.clamp(direction.y, -1, 1));
  applyLook();
  statusNode.textContent = `Review camera: ${preset.label}`;
}

function applyLook() {
  pitch = THREE.MathUtils.clamp(pitch, -1.35, 1.35);
  const direction = new THREE.Vector3(
    -Math.sin(yaw) * Math.cos(pitch),
    Math.sin(pitch),
    -Math.cos(yaw) * Math.cos(pitch),
  );
  camera.lookAt(camera.position.clone().add(direction));
}

function supportHeight(x, z) {
  for (const support of collision.support_surfaces) {
    if (x >= support.min_x && x <= support.max_x && z >= support.min_z && z <= support.max_z) {
      return support.y;
    }
  }
  return 0;
}

function blocked(x, z, radius = 0.34) {
  return collision.colliders.some((item) => (
    x >= item.min[0] - radius &&
    x <= item.max[0] + radius &&
    z >= item.min[2] - radius &&
    z <= item.max[2] + radius
  ));
}

function clampWorld(x, z) {
  const minimum = metadata.world_bounds.min;
  const maximum = metadata.world_bounds.max;
  return [
    THREE.MathUtils.clamp(x, minimum[0] + 0.34, maximum[0] - 0.34),
    THREE.MathUtils.clamp(z, minimum[2] + 0.34, maximum[2] - 0.34),
  ];
}

function moveWalker(delta) {
  const forwardInput = (keys.has("KeyW") ? 1 : 0) - (keys.has("KeyS") ? 1 : 0);
  const sideInput = (keys.has("KeyD") ? 1 : 0) - (keys.has("KeyA") ? 1 : 0);
  if (!forwardInput && !sideInput) return;
  const speed = keys.has("ShiftLeft") || keys.has("ShiftRight") ? 3.1 : 1.65;
  const forward = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
  const right = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
  const movement = forward.multiplyScalar(forwardInput).add(right.multiplyScalar(sideInput));
  if (movement.lengthSq() > 1) movement.normalize();
  movement.multiplyScalar(speed * Math.min(delta, 0.05));
  let [nextX, nextZ] = clampWorld(camera.position.x + movement.x, camera.position.z);
  if (!blocked(nextX, camera.position.z)) camera.position.x = nextX;
  [nextX, nextZ] = clampWorld(camera.position.x, camera.position.z + movement.z);
  if (!blocked(camera.position.x, nextZ)) camera.position.z = nextZ;
  camera.position.y = supportHeight(camera.position.x, camera.position.z) + 1.68;
  applyLook();
}

function segmentHitsCollider(start, end, radius, collider) {
  const minX = collider.min[0] - radius;
  const maxX = collider.max[0] + radius;
  const minZ = collider.min[2] - radius;
  const maxZ = collider.max[2] + radius;
  const dx = end[0] - start[0];
  const dz = end[2] - start[2];
  let lower = 0;
  let upper = 1;
  for (const [origin, change, low, high] of [[start[0], dx, minX, maxX], [start[2], dz, minZ, maxZ]]) {
    if (Math.abs(change) < 1e-9) {
      if (origin < low || origin > high) return false;
      continue;
    }
    let first = (low - origin) / change;
    let second = (high - origin) / change;
    if (first > second) [first, second] = [second, first];
    lower = Math.max(lower, first);
    upper = Math.min(upper, second);
    if (lower > upper) return false;
  }
  return true;
}

function runStaticRouteChecks() {
  return collision.routes.map((route) => {
    const obstructions = [];
    for (let index = 0; index < route.points.length - 1; index += 1) {
      for (const collider of collision.colliders) {
        if (segmentHitsCollider(route.points[index], route.points[index + 1], route.avatar_radius, collider)) {
          obstructions.push({ segment_index: index, collider_id: collider.id });
        }
      }
    }
    return {
      route_id: route.id,
      status: obstructions.length ? "blocked" : "clear",
      obstructions,
      point_count: route.points.length,
    };
  });
}

function addTextList(targetId, values, render) {
  const target = document.getElementById(targetId);
  target.replaceChildren();
  for (const value of values) {
    const item = document.createElement("li");
    item.innerHTML = render(value);
    target.append(item);
  }
}

function populatePanel() {
  document.title = metadata.title;
  document.getElementById("scene-title").textContent = metadata.title;
  document.getElementById("scene-subtitle").textContent = metadata.subtitle;

  addTextList("room-list", metadata.rooms, (room) => (
    `<strong>${room.name}</strong> — ${room.purpose} <em>[${room.truth_label}]</em>`
  ));

  const overlays = document.getElementById("overlay-list");
  overlays.replaceChildren();
  for (const item of metadata.overlays) {
    const card = document.createElement("div");
    card.className = "overlay-card";
    const title = document.createElement("strong");
    title.textContent = item.title;
    const body = document.createElement("span");
    body.textContent = `${item.body} [future hook only]`;
    card.append(title, body);
    overlays.append(card);
  }

  const truthCounts = document.getElementById("truth-counts");
  truthCounts.replaceChildren();
  for (const [label, count] of Object.entries(sourceTruth.label_counts)) {
    if (!count) continue;
    const chip = document.createElement("span");
    chip.className = "truth-chip";
    chip.textContent = `${label}: ${count}`;
    truthCounts.append(chip);
  }
  addTextList("source-notes", sourceTruth.source_notes, (note) => note);

  const routeChecks = runStaticRouteChecks();
  const clearCount = routeChecks.filter((item) => item.status === "clear").length;
  document.getElementById("route-summary").textContent = `${clearCount}/${routeChecks.length} static routes clear; ${collision.colliders.length} solid AABB colliders.`;
  addTextList("route-list", routeChecks, (item) => `<strong>${item.route_id}</strong>: ${item.status}, ${item.point_count} points`);

  const budgetGrid = document.getElementById("budget-grid");
  budgetGrid.replaceChildren();
  for (const [key, value] of Object.entries(budget.actual)) {
    const label = document.createElement("span");
    label.textContent = key.replace(/^max_/, "").replaceAll("_", " ");
    const amount = document.createElement("strong");
    amount.textContent = String(value);
    budgetGrid.append(label, amount);
  }

  const cameras = document.getElementById("camera-buttons");
  cameras.replaceChildren();
  metadata.cameras.forEach((preset, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = preset.label;
    button.addEventListener("click", () => setCameraPreset(index));
    cameras.append(button);
  });
  document.getElementById("toggle-routes").addEventListener("click", (event) => {
    routesVisible = !routesVisible;
    for (const line of routeVisuals) line.visible = routesVisible;
    event.currentTarget.textContent = `Routes: ${routesVisible ? "on" : "off"}`;
  });
}

function resize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const pixelWidth = Math.max(1, Math.floor(width * renderer.getPixelRatio()));
  const pixelHeight = Math.max(1, Math.floor(height * renderer.getPixelRatio()));
  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
  }
}

function animate() {
  requestAnimationFrame(animate);
  moveWalker(clock.getDelta());
  resize();
  renderer.render(scene, camera);
}

function installInput() {
  window.addEventListener("keydown", (event) => {
    keys.add(event.code);
    if (event.code === "KeyR" && !event.repeat) setCameraPreset(cameraIndex + 1);
  });
  window.addEventListener("keyup", (event) => keys.delete(event.code));
  window.addEventListener("blur", () => keys.clear());
  canvas.addEventListener("pointerdown", (event) => {
    dragging = true;
    lastPointer = [event.clientX, event.clientY];
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!dragging || !lastPointer) return;
    yaw -= (event.clientX - lastPointer[0]) * 0.004;
    pitch -= (event.clientY - lastPointer[1]) * 0.004;
    lastPointer = [event.clientX, event.clientY];
    applyLook();
  });
  const endDrag = () => {
    dragging = false;
    lastPointer = null;
  };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
}

async function start() {
  [metadata, collision, sourceTruth, budget, buildStatus] = await Promise.all([
    fetchJson("/data/scene_manifest.json"),
    fetchJson("/data/collision_nav.json"),
    fetchJson("/data/source_truth.json"),
    fetchJson("/data/resource_budget.json"),
    fetchJson("/data/build_status.json"),
  ]);
  if (
    metadata.status !== REQUIRED_BUILD_STATUS ||
    buildStatus.status !== REQUIRED_BUILD_STATUS ||
    buildStatus.final !== false ||
    buildStatus.approved !== false ||
    buildStatus.home_world_mutation !== false ||
    metadata.isolation.home_world_mutation_allowed !== false ||
    metadata.isolation.person_assets_loaded !== false
  ) {
    throw new Error("Pinned metadata does not preserve draft/isolation truth");
  }

  scene.background = color(metadata.environment.background_color);
  scene.fog = new THREE.Fog(
    color(metadata.environment.fog_color),
    metadata.environment.fog_near,
    metadata.environment.fog_far,
  );
  const materials = createMaterials(metadata.materials);
  createLights(metadata.lights);
  metadata.primitives.forEach((item) => createPrimitive(item, materials));
  createRoutes(collision.routes);
  populatePanel();
  installInput();
  setCameraPreset(0);
  statusNode.textContent = `${metadata.rooms.length} rooms · ${metadata.primitives.length} procedural meshes · isolated draft`;
  statusNode.classList.remove("error");
  window.__notebookWorldDebug = {
    backend: buildStatus.backend,
    buildId: buildStatus.build_id,
    status: buildStatus.status,
    homeWorldMutationAllowed: false,
    stripMallMutationAllowed: false,
    runtimeRegistered: false,
    peopleLoaded: 0,
    mindsLoaded: 0,
    voiceLoaded: false,
    roomCount: metadata.rooms.length,
    rooms: metadata.rooms.map((item) => item.id),
    primitiveCount: metadata.primitives.length,
    colliderCount: collision.colliders.length,
    routeCount: collision.routes.length,
    spawnCount: metadata.spawns.length,
    cameraCount: metadata.cameras.length,
    filmingMarkCount: metadata.filming_marks.length,
    getSnapshot: () => ({
      position: camera.position.toArray(),
      cameraId: metadata.cameras[cameraIndex]?.id || null,
      routeChecks: runStaticRouteChecks(),
      routesVisible,
      render: { width: canvas.width, height: canvas.height },
    }),
    runStaticRouteChecks,
    blocked,
    setCamera: (id) => {
      const index = metadata.cameras.findIndex((item) => item.id === id);
      if (index < 0) return false;
      setCameraPreset(index);
      return true;
    },
    setWalkPosition: (x, z) => {
      if (!Number.isFinite(x) || !Number.isFinite(z) || blocked(x, z)) return false;
      const [safeX, safeZ] = clampWorld(x, z);
      camera.position.set(safeX, supportHeight(safeX, safeZ) + 1.68, safeZ);
      applyLook();
      return true;
    },
  };
  window.__previewReady = true;
  animate();
}

start().catch((error) => fail("Preview failed closed: pinned metadata could not be loaded.", error));

