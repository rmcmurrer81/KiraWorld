import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const canvas = document.getElementById("world");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "low-power" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b1815);
scene.fog = new THREE.Fog(0x0b1815, 9, 18);

const camera = new THREE.PerspectiveCamera(45, 1, 0.05, 40);
camera.position.set(6.6, 3.2, 7.5);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.target.set(0, 1.05, 0);
controls.minDistance = 3.5;
controls.maxDistance = 13;
controls.maxPolarAngle = Math.PI * 0.49;

scene.add(new THREE.HemisphereLight(0xd8fff2, 0x21312b, 2.4));
const keyLight = new THREE.DirectionalLight(0xfff4d8, 3.2);
keyLight.position.set(4, 7, 4);
keyLight.castShadow = true;
scene.add(keyLight);

function material(color, roughness = 0.75) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.02 });
}

function box(name, size, position, color) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), material(color));
  mesh.name = name;
  mesh.position.set(position[0], position[1], position[2]);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

function stagedWorldAnchor(name, position) {
  const anchor = new THREE.Object3D();
  anchor.name = name;
  anchor.position.set(position[0], position[1], position[2]);
  anchor.userData.contractRole = "procedural_world_anchor";
  anchor.userData.stagedNotEvidence = true;
  scene.add(anchor);
  return anchor;
}

const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 10), material(0x365a4d, 0.95));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

box("lab_back_wall", [12, 3.2, 0.12], [0, 1.6, -3.0], 0xc5d7ce);
box("hook_backplate", [0.22, 0.38, 0.07], [-3.05, 1.82, -2.88], 0x7f8c87);
const hook = new THREE.Mesh(
  new THREE.TorusGeometry(0.12, 0.025, 10, 24, Math.PI * 1.25),
  new THREE.MeshStandardMaterial({ color: 0xc3cbc7, roughness: 0.3, metalness: 0.7 }),
);
hook.name = "wardrobe_lab_wall_hook_001";
hook.rotation.set(Math.PI / 2, 0, Math.PI * 0.15);
hook.position.set(-3.05, 1.72, -2.72);
scene.add(hook);
stagedWorldAnchor("bathroom_wall_hook", [-3.05, 1.72, -2.72]);
stagedWorldAnchor("bathroom_wall_hook_approach", [-2.15, 0, -1.75]);

box("bed_frame", [3.2, 0.42, 2.0], [2.7, 0.25, -1.75], 0x5b3b2b);
box("bed_mattress_support_surface", [3.05, 0.34, 1.86], [2.7, 0.62, -1.75], 0xe6e5dd);
box("bed_pillow", [0.95, 0.19, 0.62], [3.55, 0.88, -2.18], 0xb7d9cc);
stagedWorldAnchor("bed_soft_goods_place_anchor", [2.7, 0.83, -1.75]);
stagedWorldAnchor("bed_mattress_support_surface", [2.7, 0.79, -1.75]);
stagedWorldAnchor("bed_soft_goods_settle_volume", [2.7, 1.02, -1.75]);
stagedWorldAnchor("sit_approach", [1.4, 0, -0.95]);
stagedWorldAnchor("sit_support", [2.0, 0.82, -1.3]);

const lane = new THREE.Mesh(
  new THREE.PlaneGeometry(3.2, 0.8),
  new THREE.MeshBasicMaterial({ color: 0x54b998, transparent: true, opacity: 0.12, side: THREE.DoubleSide }),
);
lane.name = "walk_evidence_lane_placeholder";
lane.rotation.x = -Math.PI / 2;
lane.position.set(0.2, 0.012, 1.0);
scene.add(lane);
stagedWorldAnchor("walk_start", [-1.4, 0, 1.0]);
stagedWorldAnchor("walk_end", [1.5, 0, 1.0]);
stagedWorldAnchor("turn_center", [1.2, 0, 1.0]);

const marker = new THREE.Mesh(
  new THREE.OctahedronGeometry(0.16, 0),
  new THREE.MeshBasicMaterial({ color: 0xffb646, wireframe: true, transparent: true, opacity: 0.9 }),
);
marker.name = "inspection_marker_not_evidence";
scene.add(marker);

const markerPositions = {
  hook: [-3.05, 2.2, -2.55],
  between_hook_and_body: [-1.85, 1.4, -1.4],
  body: [-0.75, 1.7, -0.55],
  walk_lane: [0.0, 0.35, 1.0],
  turn_lane: [1.2, 0.35, 1.0],
  bed: [2.7, 1.15, -1.6],
  choice: [1.0, 1.5, -0.8],
  overview: [0.0, 2.5, 0.0],
};

const loader = new GLTFLoader();

function visibleBounds(root) {
  root.updateMatrixWorld(true);
  const bounds = new THREE.Box3();
  root.traverse((node) => {
    if (!node.isMesh || !node.visible || !node.geometry) {
      return;
    }
    if (!node.geometry.boundingBox) {
      node.geometry.computeBoundingBox();
    }
    if (node.geometry.boundingBox) {
      bounds.union(node.geometry.boundingBox.clone().applyMatrix4(node.matrixWorld));
    }
  });
  return bounds;
}

function normalizeModel(root, targetHeight, targetPosition) {
  const bounds = visibleBounds(root);
  const size = new THREE.Vector3();
  bounds.getSize(size);
  if (!Number.isFinite(size.y) || size.y <= 0) {
    throw new Error("Model has no measurable height.");
  }
  const scale = targetHeight / size.y;
  root.scale.setScalar(scale);
  const scaled = visibleBounds(root);
  const center = new THREE.Vector3();
  scaled.getCenter(center);
  root.position.x += targetPosition[0] - center.x;
  root.position.y += targetPosition[1] - scaled.min.y;
  root.position.z += targetPosition[2] - center.z;
  root.traverse((node) => {
    if (node.isMesh) {
      node.castShadow = true;
      node.receiveShadow = true;
    }
  });
}

function loadModel(url, targetHeight, targetPosition, name, prepare = null) {
  return new Promise((resolve, reject) => {
    loader.load(
      url,
      (gltf) => {
        gltf.scene.name = name;
        if (prepare) {
          prepare(gltf.scene);
        }
        normalizeModel(gltf.scene, targetHeight, targetPosition);
        scene.add(gltf.scene);
        resolve(gltf.scene);
      },
      undefined,
      reject,
    );
  });
}

function keepOneHangingRobeReference(root) {
  const robeMeshPrefixes = [
    "shared_white_bath_robe_v1_hook_loop",
    "robe_hanging_back_panel_soft_mesh",
    "robe_hanging_left_front_panel_soft_mesh",
    "robe_hanging_right_front_panel_soft_mesh",
    "robe_hanging_left_sleeve_opening_soft_mesh",
    "robe_hanging_right_sleeve_opening_soft_mesh",
    "robe_hanging_shawl_collar_left",
    "robe_hanging_shawl_collar_right",
    "robe_hanging_loose_belt_left_end",
    "robe_hanging_loose_belt_right_end",
  ];
  let visibleMeshCount = 0;
  root.traverse((node) => {
    if (!node.isMesh) {
      return;
    }
    const name = String(node.name || "");
    node.visible = robeMeshPrefixes.some((prefix) => name.startsWith(prefix));
    if (node.visible) {
      visibleMeshCount += 1;
    }
  });
  if (visibleMeshCount === 0) {
    throw new Error("Pinned robe proof has no named hanging-robe meshes.");
  }
}

const assetStatus = document.getElementById("asset-status");
Promise.all([
  loadModel("/assets/kira-current-body.glb", 1.72, [-0.75, 0, -0.55], "kira_current_body_read_only"),
  loadModel(
    "/assets/robe-draft-proof.glb",
    1.18,
    [-3.05, 0.57, -2.55],
    "one_hanging_robe_static_reference_not_wearable",
    keepOneHangingRobeReference,
  ),
]).then(() => {
  assetStatus.textContent = "Pinned body and one hanging robe reference loaded. Neither asset was modified.";
}).catch((error) => {
  assetStatus.textContent = "A pinned model could not load: " + String(error.message || error);
  assetStatus.classList.add("error");
});

let machine = null;
let currentState = null;
let history = [];
let stateById = new Map();

const stateLabel = document.getElementById("state-label");
const stateOwner = document.getElementById("state-owner");
const requiredSignals = document.getElementById("required-signals");
const blockers = document.getElementById("blockers");
const proofCount = document.getElementById("proof-count");
const proofFill = document.getElementById("proof-fill");
const claimStatus = document.getElementById("claim-status");
const choices = document.getElementById("choices");
const nextButton = document.getElementById("next");
const backButton = document.getElementById("back");
const stateList = document.getElementById("state-list");

function fillList(element, entries) {
  element.replaceChildren();
  entries.forEach((entry) => {
    const li = document.createElement("li");
    li.textContent = entry;
    element.appendChild(li);
  });
}

function renderStateList() {
  stateList.replaceChildren();
  machine.states.forEach((state) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = state.label;
    button.classList.toggle("current", state.id === currentState.id);
    button.addEventListener("click", () => selectState(state.id, true));
    li.appendChild(button);
    stateList.appendChild(li);
  });
}

function selectState(id, remember) {
  const state = stateById.get(id);
  if (!state) {
    return;
  }
  if (remember && currentState && currentState.id !== id) {
    history.push(currentState.id);
  }
  currentState = state;
  stateLabel.textContent = state.label;
  stateOwner.textContent = "Contract owner: " + state.owner + " · status: " + state.status;
  fillList(requiredSignals, state.required_signals);
  fillList(blockers, state.blockers);
  const verified = state.verified_signals.length;
  const needed = state.required_signals.length;
  proofCount.textContent = String(verified) + " of " + String(needed) + " signals recorded";
  proofFill.style.width = needed ? String((verified / needed) * 100) + "%" : "0%";
  claimStatus.textContent = state.claim_allowed ? "REVIEW REQUIRED" : "BLOCKED";
  choices.replaceChildren();
  if (state.next.length > 1) {
    state.next.forEach((nextId) => {
      const target = stateById.get(nextId);
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Inspect possible branch: " + target.label;
      button.addEventListener("click", () => selectState(nextId, true));
      choices.appendChild(button);
    });
  }
  nextButton.disabled = state.next.length !== 1;
  nextButton.textContent = state.next.length === 0 ? "End of proposal" : state.next.length > 1 ? "Choose a branch" : "Inspect next";
  backButton.disabled = history.length === 0;
  const position = markerPositions[state.visual_zone] || markerPositions.overview;
  marker.position.set(position[0], position[1], position[2]);
  renderStateList();
}

document.getElementById("next").addEventListener("click", () => {
  if (currentState && currentState.next.length === 1) {
    selectState(currentState.next[0], true);
  }
});

document.getElementById("back").addEventListener("click", () => {
  const previous = history.pop();
  if (previous) {
    selectState(previous, false);
  }
});

document.getElementById("reset").addEventListener("click", () => {
  history = [];
  selectState(machine.initial_state, false);
});

fetch("/data/wardrobe_state_machine.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) {
      throw new Error("state contract HTTP " + String(response.status));
    }
    return response.json();
  })
  .then((data) => {
    machine = data;
    stateById = new Map(data.states.map((state) => [state.id, state]));
    selectState(data.initial_state, false);
  })
  .catch((error) => {
    stateLabel.textContent = "State contract unavailable";
    stateOwner.textContent = String(error.message || error);
    claimStatus.textContent = "BLOCKED";
    nextButton.disabled = true;
  });

function resize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (canvas.width !== Math.floor(width * renderer.getPixelRatio()) || canvas.height !== Math.floor(height * renderer.getPixelRatio())) {
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
  }
}

function animate() {
  resize();
  controls.update();
  marker.rotation.y += 0.008;
  marker.rotation.x += 0.004;
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

animate();
