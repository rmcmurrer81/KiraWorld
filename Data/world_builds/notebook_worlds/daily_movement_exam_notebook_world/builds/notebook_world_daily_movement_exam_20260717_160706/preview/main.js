import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { PointerLockControls } from "three/addons/controls/PointerLockControls.js";

const PROGRAM_URL = "/data/scene_program.json";
const WALK_RADIUS = 0.34;
const WALK_EYE_HEIGHT = 1.68;
const canvas = document.getElementById("world");
const routeSelect = document.getElementById("route-select");
const cameraSelect = document.getElementById("camera-select");
const routeResult = document.getElementById("route-result");
const stationList = document.getElementById("station-list");
const truthList = document.getElementById("truth-list");
const loadStatus = document.getElementById("load-status");
const walkHint = document.getElementById("walk-hint");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "low-power" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, 1, 0.05, 100);
camera.position.set(10, 5.2, 10);

const orbit = new OrbitControls(camera, canvas);
orbit.enableDamping = true;
orbit.target.set(0, 0.8, 0);
orbit.maxPolarAngle = Math.PI * 0.49;
orbit.minDistance = 2.2;
orbit.maxDistance = 30;

const pointer = new PointerLockControls(camera, canvas);
const clock = new THREE.Clock();
const pressed = new Set();
let program = null;
let routeProbe = null;
let routeAnimation = null;
let walkPosition = new THREE.Vector3(0, WALK_EYE_HEIGHT, 9.7);
let lastCollision = "";

function standardMaterial(spec) {
  return new THREE.MeshStandardMaterial({
    color: spec.color,
    roughness: Number(spec.roughness ?? 0.8),
    metalness: Number(spec.metalness ?? 0),
    transparent: Number(spec.opacity ?? 1) < 1,
    opacity: Number(spec.opacity ?? 1),
  });
}

function makePrimitive(spec, materials) {
  let geometry;
  if (spec.primitive === "box") {
    geometry = new THREE.BoxGeometry(...spec.size);
  } else if (spec.primitive === "cylinder") {
    geometry = new THREE.CylinderGeometry(spec.radius, spec.radius, spec.height, spec.segments || 16);
  } else {
    throw new Error(`Unsupported primitive ${spec.primitive}`);
  }
  const mesh = new THREE.Mesh(geometry, materials.get(spec.material_id));
  mesh.name = spec.id;
  mesh.position.set(...spec.position);
  mesh.rotation.set(...(spec.rotation || [0, 0, 0]));
  mesh.castShadow = spec.category !== "floor_mark";
  mesh.receiveShadow = true;
  mesh.userData.truthLabel = spec.truth_label;
  mesh.userData.sourceNote = spec.source_note;
  scene.add(mesh);
  return mesh;
}

function addLights() {
  program.lights.forEach((spec) => {
    let light;
    if (spec.type === "hemisphere") {
      light = new THREE.HemisphereLight(spec.sky_color, spec.ground_color, spec.intensity);
    } else {
      light = new THREE.DirectionalLight(spec.color, spec.intensity);
      light.position.set(...spec.position);
      light.castShadow = true;
      light.shadow.mapSize.set(1024, 1024);
    }
    light.name = spec.id;
    scene.add(light);
  });
}

function collisionAt(x, z, radius = WALK_RADIUS) {
  return program.colliders.find((collider) =>
    x >= collider.min[0] - radius && x <= collider.max[0] + radius &&
    z >= collider.min[2] - radius && z <= collider.max[2] + radius
  ) || null;
}

function supportedAt(x, z) {
  return program.support_surfaces.some((surface) =>
    x >= surface.min_x + WALK_RADIUS && x <= surface.max_x - WALK_RADIUS &&
    z >= surface.min_z + WALK_RADIUS && z <= surface.max_z - WALK_RADIUS
  );
}

function routeSamples(route, step = 0.05) {
  const samples = [];
  for (let index = 1; index < route.points.length; index += 1) {
    const a = route.points[index - 1];
    const b = route.points[index];
    const distance = Math.hypot(b[0] - a[0], b[2] - a[2]);
    const count = Math.max(1, Math.ceil(distance / step));
    for (let sample = index === 1 ? 0 : 1; sample <= count; sample += 1) {
      const t = sample / count;
      samples.push(new THREE.Vector3(
        THREE.MathUtils.lerp(a[0], b[0], t),
        THREE.MathUtils.lerp(a[1], b[1], t),
        THREE.MathUtils.lerp(a[2], b[2], t),
      ));
    }
  }
  return samples;
}

function checkRoute(route) {
  const samples = routeSamples(route);
  for (const sample of samples) {
    const collider = collisionAt(sample.x, sample.z, route.avatar_radius);
    if (collider) return { passed: false, reason: `intersects ${collider.id}`, samples };
    if (!supportedAt(sample.x, sample.z)) return { passed: false, reason: "leaves a declared support surface", samples };
  }
  return { passed: true, reason: `${samples.length} samples clear`, samples };
}

function drawRoutes() {
  program.routes.forEach((route) => {
    const check = checkRoute(route);
    const geometry = new THREE.BufferGeometry().setFromPoints(route.points.map((point) => new THREE.Vector3(point[0], point[1] + 0.035, point[2])));
    const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: check.passed ? 0x70d7b0 : 0xe57373, transparent: true, opacity: 0.55 }));
    line.name = `route_${route.id}`;
    scene.add(line);
  });
}

function makeRouteProbe() {
  const group = new THREE.Group();
  group.name = "non_person_clearance_probe";
  const material = new THREE.MeshStandardMaterial({ color: 0x73e6ff, emissive: 0x123c48, roughness: 0.45 });
  const cylinder = new THREE.Mesh(new THREE.CylinderGeometry(WALK_RADIUS, WALK_RADIUS, 1.05, 20), material);
  cylinder.position.y = 0.7;
  const top = new THREE.Mesh(new THREE.SphereGeometry(WALK_RADIUS, 20, 12), material);
  top.position.y = 1.225;
  const bottom = new THREE.Mesh(new THREE.SphereGeometry(WALK_RADIUS, 20, 12), material);
  bottom.position.y = 0.175;
  group.add(cylinder, top, bottom);
  group.visible = false;
  scene.add(group);
  return group;
}

function runRoute(route) {
  const check = checkRoute(route);
  routeResult.className = `result ${check.passed ? "pass" : "fail"}`;
  routeResult.textContent = `${check.passed ? "PASS" : "BLOCKED"}: ${route.label} — ${check.reason}. Static geometry only.`;
  routeAnimation = check.passed ? { samples: check.samples, index: 0, accumulator: 0 } : null;
  routeProbe.visible = Boolean(routeAnimation);
  if (routeAnimation) routeProbe.position.copy(routeAnimation.samples[0]);
  return { route_id: route.id, passed: check.passed, reason: check.reason, sample_count: check.samples.length };
}

function setCamera(spec) {
  pointer.unlock();
  orbit.enabled = true;
  camera.position.set(...spec.position);
  orbit.target.set(...spec.target);
  camera.fov = spec.fov;
  camera.updateProjectionMatrix();
  orbit.update();
}

function buildUi() {
  program.routes.forEach((route) => routeSelect.add(new Option(route.label, route.id)));
  program.cameras.forEach((preset) => cameraSelect.add(new Option(preset.label, preset.id)));
  program.filming_marks.forEach((station) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = station.label;
    button.title = station.source_note;
    button.addEventListener("click", () => {
      const primitive = program.primitives.find((item) => item.id === station.primitive_id);
      if (!primitive) return;
      pointer.unlock();
      orbit.enabled = true;
      camera.position.set(primitive.position[0] + 3.4, 2.5, primitive.position[2] + 3.5);
      orbit.target.set(primitive.position[0], 0.8, primitive.position[2]);
      orbit.update();
      routeResult.className = "result";
      routeResult.textContent = `${station.label}: review mark only. ${station.source_note}`;
    });
    stationList.appendChild(button);
  });
  program.overlays.forEach((overlay) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${overlay.title}:</strong> ${overlay.body}`;
    truthList.appendChild(li);
  });
}

function enterWalk() {
  routeAnimation = null;
  routeProbe.visible = false;
  orbit.enabled = false;
  camera.position.copy(walkPosition);
  pointer.lock();
}

function updateWalk(delta) {
  if (!pointer.isLocked || !program) return;
  const forwardInput = Number(pressed.has("KeyW")) - Number(pressed.has("KeyS"));
  const sideInput = Number(pressed.has("KeyD")) - Number(pressed.has("KeyA"));
  if (!forwardInput && !sideInput) return;
  const speed = pressed.has("ShiftLeft") || pressed.has("ShiftRight") ? 3.2 : 1.75;
  const forward = new THREE.Vector3();
  camera.getWorldDirection(forward);
  forward.y = 0;
  forward.normalize();
  const right = new THREE.Vector3(-forward.z, 0, forward.x);
  const movement = forward.multiplyScalar(forwardInput).add(right.multiplyScalar(sideInput));
  if (movement.lengthSq() > 1) movement.normalize();
  movement.multiplyScalar(speed * delta);
  const candidate = camera.position.clone().add(movement);
  const collision = collisionAt(candidate.x, candidate.z);
  if (!collision && supportedAt(candidate.x, candidate.z)) {
    camera.position.set(candidate.x, WALK_EYE_HEIGHT, candidate.z);
    walkPosition.copy(camera.position);
    lastCollision = "";
  } else {
    lastCollision = collision ? collision.id : "support boundary";
    walkHint.textContent = `Blocked by ${lastCollision}. Esc exits owner walk review.`;
  }
}

function updateRouteProbe(delta) {
  if (!routeAnimation) return;
  routeAnimation.accumulator += delta * 22;
  while (routeAnimation.accumulator >= 1 && routeAnimation.index < routeAnimation.samples.length - 1) {
    routeAnimation.accumulator -= 1;
    routeAnimation.index += 1;
  }
  routeProbe.position.copy(routeAnimation.samples[routeAnimation.index]);
  if (routeAnimation.index >= routeAnimation.samples.length - 1) routeAnimation = null;
}

async function init() {
  const response = await fetch(PROGRAM_URL, { cache: "no-store" });
  if (!response.ok) throw new Error(`Scene contract returned HTTP ${response.status}`);
  program = await response.json();
  scene.background = new THREE.Color(program.environment.background_color);
  scene.fog = new THREE.Fog(program.environment.fog_color, program.environment.fog_near, program.environment.fog_far);
  const materials = new Map(program.materials.map((spec) => [spec.id, standardMaterial(spec)]));
  addLights();
  program.primitives.forEach((spec) => makePrimitive(spec, materials));
  drawRoutes();
  routeProbe = makeRouteProbe();
  buildUi();
  setCamera(program.cameras[0]);
  const results = program.routes.map(checkRoute);
  const clear = results.filter((result) => result.passed).length;
  loadStatus.textContent = `${program.primitives.length} primitives, ${program.colliders.length} colliders, ${clear}/${program.routes.length} clearance routes pass. No person assets requested.`;
  window.__dailyMovementExamDebug = {
    worldId: program.world_id,
    buildStatus: program.status,
    peopleLoaded: 0,
    mindsLoaded: 0,
    voiceLoaded: false,
    homeWorldLoaded: false,
    runtimeRegistered: false,
    personActivationAllowed: false,
    bodySkillExecutionAllowed: false,
    sceneBudget: program.scene_budget,
    isolation: program.isolation,
    runRouteCheck(id) {
      const route = program.routes.find((item) => item.id === id);
      return route ? runRoute(route) : { route_id: id, passed: false, reason: "unknown route" };
    },
    runAllRouteChecks() {
      return program.routes.map((route) => ({ route_id: route.id, ...checkRoute(route) })).map(({ samples, ...result }) => ({ ...result, sample_count: samples.length }));
    },
    collisionAt(x, z, radius = WALK_RADIUS) {
      return collisionAt(x, z, radius)?.id || null;
    },
    stationCount: program.filming_marks.length,
  };
  window.__previewReady = true;
}

document.getElementById("run-route").addEventListener("click", () => {
  const route = program.routes.find((item) => item.id === routeSelect.value);
  if (route) runRoute(route);
});
document.getElementById("set-camera").addEventListener("click", () => {
  const preset = program.cameras.find((item) => item.id === cameraSelect.value);
  if (preset) setCamera(preset);
});
document.getElementById("walk-mode").addEventListener("click", enterWalk);
pointer.addEventListener("lock", () => {
  walkHint.textContent = "Owner walk review: WASD, Shift, mouse look; Esc exits. No Kira or person is loaded.";
});
pointer.addEventListener("unlock", () => {
  orbit.enabled = true;
  orbit.target.copy(camera.position).add(new THREE.Vector3(0, -0.5, -3).applyQuaternion(camera.quaternion));
  walkHint.textContent = lastCollision ? `Orbit review restored. Last block: ${lastCollision}.` : "Orbit review restored.";
});
addEventListener("keydown", (event) => pressed.add(event.code));
addEventListener("keyup", (event) => pressed.delete(event.code));
addEventListener("resize", resize);

function resize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / Math.max(1, height);
  camera.updateProjectionMatrix();
}

function animate() {
  const delta = Math.min(clock.getDelta(), 0.04);
  updateWalk(delta);
  updateRouteProbe(delta);
  orbit.update();
  resize();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

window.__previewReady = false;
init().catch((error) => {
  loadStatus.textContent = `Preview failed closed: ${String(error.message || error)}`;
  loadStatus.style.color = "#ff9a93";
});
animate();
