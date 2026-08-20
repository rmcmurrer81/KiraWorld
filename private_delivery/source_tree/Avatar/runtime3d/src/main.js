import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import "./style.css";

const params = new URLSearchParams(location.search);
const candidateId = params.get("candidate") || "ladybug_marinette_expanded_smoke";
const manualMode = params.get("manual") === "1";
const embeddedMode = params.get("embedded") === "1";
const forceOrbMode = params.get("orb") === "1";
const displayName = params.get("name") || candidateId.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
const AVATAR_TARGET_HEIGHT_METERS = 1.57;
const selfTestMode = params.get("selftest") === "1";
const lipSyncSampleText = params.get("sampleText") || "Hi, I am ready to test standing, sitting, fingers, walking, jogging, and speech.";
if (params.get("title")) document.title = params.get("title");
if (embeddedMode) document.body.classList.add("embedded");
document.querySelector("#name").textContent = displayName;

const canvas = document.querySelector("#stage");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x171c21);
scene.fog = new THREE.Fog(0x171c21, 10, 24);
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 50);
camera.position.set(embeddedMode ? 0 : 6.4, embeddedMode ? 1.24 : 3.6, embeddedMode ? 2.18 : 7.8);
camera.lookAt(0, embeddedMode ? 1.02 : 1.55, embeddedMode ? 0.24 : 0);

scene.add(new THREE.HemisphereLight(0xddeeff, 0x403830, 2.0));
const key = new THREE.DirectionalLight(0xfff1d4, 3.2);
key.position.set(4, 7, 4); key.castShadow = true; scene.add(key);
const fill = new THREE.PointLight(0x87bde6, 18, 12); fill.position.set(-4, 3, 2); scene.add(fill);

const floor = new THREE.Mesh(new THREE.PlaneGeometry(24, 18), new THREE.MeshStandardMaterial({ color: 0x354048, roughness: 0.92 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
const rug = new THREE.Mesh(new THREE.PlaneGeometry(5.5, 4), new THREE.MeshStandardMaterial({ color: 0x6b4650, roughness: 1 }));
rug.rotation.x = -Math.PI / 2; rug.position.y = 0.006; rug.receiveShadow = true; scene.add(rug);

function box(w, h, d, color, x, y, z) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color, roughness: 0.78 }));
  mesh.position.set(x, y, z); mesh.castShadow = mesh.receiveShadow = true; scene.add(mesh); return mesh;
}
box(embeddedMode ? 3.0 : 4.0, 0.16, embeddedMode ? 1.05 : 1.4, 0x6f4b37, -3.35, 1.28, -2.55);
box(0.14, 1.28, 0.14, 0x4d3427, -4.55, 0.64, -2.9); box(0.14, 1.28, 0.14, 0x4d3427, -2.15, 0.64, -2.9);
box(0.14, 1.28, 0.14, 0x4d3427, -4.55, 0.64, -2.2); box(0.14, 1.28, 0.14, 0x4d3427, -2.15, 0.64, -2.2);
const monitor = box(1.5, 0.92, 0.08, 0x15191e, -3.1, 2.15, -2.45);
const screen = new THREE.Mesh(new THREE.PlaneGeometry(1.32, 0.73), new THREE.MeshBasicMaterial({ color: 0x6ba5bd }));
screen.position.set(-3.1, 2.15, -2.405); scene.add(screen);
box(1.05, 0.08, 0.42, 0x20252a, -3.1, 1.58, -1.92);
box(1.25, 0.12, 1.1, 0x45505a, -2.9, 0.82, -0.8); box(0.12, 0.82, 0.12, 0x343b42, -3.38, 0.4, -0.8); box(0.12, 0.82, 0.12, 0x343b42, -2.42, 0.4, -0.8);
box(1.25, 1.45, 0.14, 0x45505a, -2.9, 1.48, -1.28);
box(0.9, 0.045, 0.3, 0x20252a, -3.1, 1.57, -1.82);
box(2.8, 3.5, 0.55, 0x5a4031, 4.25, 1.75, -2.7);
for (let y = 0.35; y < 3.4; y += 0.72) box(2.65, 0.08, 0.48, 0x3f2b22, 4.25, y, -2.36);
for (let i = 0; i < 15; i++) box(0.12 + (i % 3) * 0.03, 0.42 + (i % 4) * 0.05, 0.3, [0x356f82,0x9b4f52,0xc19a4a,0x547247][i%4], 3.15 + (i%5)*0.52, 0.58 + Math.floor(i/5)*0.72, -2.05);

const palette = {
  civilian: { top: 0x313942, pants: 0xd95d70, accent: 0xe9ecef },
  hero: { top: candidateId.includes("kara") ? 0x204e68 : 0xd52d3b, pants: candidateId.includes("kara") ? 0x204e68 : 0xd52d3b, accent: 0xf3c73f },
  sleepwear: { top: 0x7388a8, pants: 0x4e5f7a, accent: 0xd8e0eb },
};
const skin = new THREE.MeshStandardMaterial({ color: candidateId.includes("kara") ? 0xf0c7aa : 0xe7b395, roughness: 0.72 });
const hair = new THREE.MeshStandardMaterial({ color: candidateId.includes("kara") ? 0xe9cf61 : 0x172a46, roughness: 0.9 });
const mats = { top: null, pants: null, accent: null };

function mesh(geometry, material, parent, y = 0) {
  const m = new THREE.Mesh(geometry, material); m.position.y = y; m.castShadow = true; m.receiveShadow = true; parent.add(m); return m;
}
function limb(radius, length, material, parent) {
  const pivot = new THREE.Group(); parent.add(pivot);
  const part = mesh(new THREE.CapsuleGeometry(radius, length - radius * 2, 6, 12), material, pivot, -length / 2);
  return { pivot, part };
}

const avatar = new THREE.Group(); avatar.position.set(0, 0, 0.4); scene.add(avatar);
let riggedRoot = null;
let riggedMixer = null;
let riggedClips = [];
let riggedAction = null;
let loadedModelUrl = "";
const riggedBasePosition = new THREE.Vector3();
let riggedBaseRotationY = 0;
const riggedLoader = new GLTFLoader();
const textureLoader = new THREE.TextureLoader();
const poseMaterial = new THREE.SpriteMaterial({ transparent: true, depthWrite: false, alphaTest: 0.035 });
const poseSprite = new THREE.Sprite(poseMaterial);
poseSprite.position.set(0, 1.75, 0.4);
poseSprite.visible = false;
scene.add(poseSprite);
const orbGroup = new THREE.Group();
orbGroup.visible = false;
orbGroup.position.set(0, 1.42, 0.4);
const orbCore = new THREE.Mesh(
  new THREE.SphereGeometry(0.28, 32, 20),
  new THREE.MeshStandardMaterial({ color: 0x75d9ff, emissive: 0x124a75, emissiveIntensity: 1.15, roughness: 0.2, metalness: 0.05 })
);
orbGroup.add(orbCore);
const orbHalo = new THREE.Mesh(
  new THREE.TorusGeometry(0.42, 0.012, 8, 64),
  new THREE.MeshBasicMaterial({ color: 0x9df0ff, transparent: true, opacity: 0.58 })
);
orbHalo.rotation.x = Math.PI / 2;
orbGroup.add(orbHalo);
const orbHalo2 = orbHalo.clone();
orbHalo2.rotation.set(Math.PI / 2, Math.PI / 2.7, 0);
orbGroup.add(orbHalo2);
scene.add(orbGroup);
let loadedPoseManifestUrl = "";
let poseTextures = new Map();
let currentPoseKey = "";

function findRiggedClip(next) {
  const exact = riggedClips.find(clip => clip.name.toLowerCase() === String(next || "").toLowerCase());
  if (exact) return exact;
  const prefixed = riggedClips.find(clip => clip.name.toLowerCase().startsWith(`${String(next || "").toLowerCase()}_`));
  if (prefixed) return prefixed;
  const terms = {
    idle: ["idle", "stand", "breath"],
    stand: ["idle", "stand", "breath"],
    walk: ["walk", "walking", "locomotion"],
    jog: ["jog", "run", "walk", "locomotion"],
    wave: ["wave", "greet", "hello"],
    sit: ["sit", "sitting"],
    open_hand: ["hand", "open", "wave", "idle"],
    close_hand: ["hand", "fist", "close", "idle"],
    read_book: ["read", "book"],
    read_magazine: ["read", "magazine", "book"],
    use_computer: ["type", "typing", "computer", "desk"],
    talking: ["talk", "speak", "conversation", "idle"],
  }[next] || [next];
  return riggedClips.find(clip => terms.some(term => clip.name.toLowerCase().includes(term)))
    || riggedClips.find(clip => clip.name.toLowerCase().includes("idle"))
    || riggedClips[0];
}

function playRiggedAction(next) {
  if (!riggedMixer || !riggedClips.length) return;
  const clip = findRiggedClip(next);
  if (!clip) return;
  const nextAction = riggedMixer.clipAction(clip);
  if (riggedAction === nextAction && nextAction.isRunning()) return;
  if (riggedAction) riggedAction.fadeOut(0.28);
  nextAction.reset().fadeIn(0.28);
  if (next === "wave") {
    nextAction.setLoop(THREE.LoopOnce, 1);
    nextAction.clampWhenFinished = true;
  } else {
    nextAction.setLoop(THREE.LoopRepeat, Infinity);
    nextAction.clampWhenFinished = false;
  }
  nextAction.play();
  riggedAction = nextAction;
}

function applyRiggedForm(nextForm) {
  if (!riggedRoot) return;
  const tags = ["civilian", "hero", "sleepwear", "pajama", "pyjama"];
  let hasTaggedOutfits = false;
  riggedRoot.traverse(node => {
    if (node.isMesh && tags.some(tag => node.name.toLowerCase().includes(tag))) hasTaggedOutfits = true;
  });
  if (!hasTaggedOutfits) return;
  riggedRoot.traverse(node => {
    if (!node.isMesh) return;
    const name = node.name.toLowerCase();
    const tagged = tags.some(tag => name.includes(tag));
    if (!tagged) return;
    const wantedTags = nextForm === "sleepwear" ? ["sleepwear", "pajama", "pyjama"] : [nextForm];
    node.visible = wantedTags.some(tag => name.includes(tag));
  });
}

function loadRiggedModel(url) {
  if (!url || url === loadedModelUrl) return;
  loadedModelUrl = url;
  document.querySelector("#status").textContent = "LOADING RIGGED MODEL";
  riggedLoader.load(url, gltf => {
    if (riggedRoot) scene.remove(riggedRoot);
    riggedRoot = gltf.scene;
    riggedClips = gltf.animations || [];
    riggedRoot.traverse(node => {
      if (node.isMesh) { node.castShadow = true; node.receiveShadow = true; }
    });
    const bounds = new THREE.Box3().setFromObject(riggedRoot);
    const size = bounds.getSize(new THREE.Vector3());
    const scale = size.y > 0 ? AVATAR_TARGET_HEIGHT_METERS / size.y : 1;
    riggedRoot.scale.setScalar(scale);
    const scaledBounds = new THREE.Box3().setFromObject(riggedRoot);
    const center = scaledBounds.getCenter(new THREE.Vector3());
    riggedRoot.position.set(-center.x, -scaledBounds.min.y, 0.4 - center.z);
    riggedBasePosition.copy(riggedRoot.position);
    riggedBaseRotationY = riggedRoot.rotation.y;
    scene.add(riggedRoot);
    avatar.visible = false;
    poseSprite.visible = false;
    orbGroup.visible = false;
    riggedMixer = new THREE.AnimationMixer(riggedRoot);
    applyRiggedForm(form);
    playRiggedAction(action);
    document.querySelector("#status").textContent = riggedClips.length ? "ANIMATED 3D MODEL" : "3D MODEL V1";
  }, undefined, error => {
    console.warn("Rigged avatar failed to load; using generated pose fallback.", error);
    loadedModelUrl = "";
    poseSprite.visible = poseTextures.size > 0;
    avatar.visible = !poseSprite.visible;
    document.querySelector("#status").textContent = poseSprite.visible ? "GENERATED 2D POSE" : "PROCEDURAL V1";
  });
}

function showBodylessOrb(reason = "BODY PENDING") {
  if (riggedRoot) {
    scene.remove(riggedRoot);
    riggedRoot = null;
    riggedMixer = null;
    riggedClips = [];
    riggedAction = null;
    loadedModelUrl = "";
  }
  avatar.visible = false;
  poseSprite.visible = false;
  orbGroup.visible = true;
  document.querySelector("#status").textContent = reason;
}

function webAssetUrl(path) {
  if (!path) return "";
  return path.startsWith("/") ? path : `/${path}`;
}

function loadTexture(url) {
  return new Promise((resolve, reject) => {
    textureLoader.load(url, texture => {
      texture.colorSpace = THREE.SRGBColorSpace;
      resolve(texture);
    }, undefined, reject);
  });
}

async function loadPoseManifest(url) {
  if (!url || url === loadedPoseManifestUrl || riggedRoot) return;
  const previousUrl = loadedPoseManifestUrl;
  const hadVisibleAppearance = poseSprite.visible || avatar.visible;
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Pose manifest returned ${response.status}`);
    const manifest = await response.json();
    const pending = [];
    const nextTextures = new Map();
    for (const [formName, formData] of Object.entries(manifest.forms || {})) {
      for (const [poseName, poseData] of Object.entries(formData.poses || {})) {
        if (!poseData?.file || poseData.status !== "ready") continue;
        pending.push(
          loadTexture(webAssetUrl(poseData.file)).then(texture => nextTextures.set(`${formName}:${poseName}`, texture))
        );
      }
    }
    await Promise.all(pending);
    if (!nextTextures.size || riggedRoot) throw new Error("No generated pose textures were found.");
    loadedPoseManifestUrl = url;
    poseTextures = nextTextures;
    currentPoseKey = "";
    poseSprite.visible = true;
    avatar.visible = false;
    orbGroup.visible = false;
    updatePoseSprite(performance.now() / 1000);
    document.querySelector("#status").textContent = "GENERATED 2D POSE";
  } catch (error) {
    console.warn("Generated pose fallback failed to load.", error);
    loadedPoseManifestUrl = previousUrl;
    if (!hadVisibleAppearance) {
      poseSprite.visible = false;
      avatar.visible = !forceOrbMode;
      orbGroup.visible = forceOrbMode;
    }
    document.querySelector("#status").textContent = poseSprite.visible ? "GENERATED 2D POSE" : "PROCEDURAL V1";
  }
}

function poseNameForAction(t) {
  if (action === "wave") return Math.floor(t * 3.2) % 2 ? "wave_1" : "wave_2";
  if (action === "talking") return Math.floor(t * 2.6) % 2 ? "talking" : "neutral";
  if (action === "idle") {
    const idlePhase = Math.floor(t) % 12;
    if (idlePhase === 8) return "look_left";
    if (idlePhase === 9) return "look_right";
  }
  return "neutral";
}

function updatePoseSprite(t) {
  if (!poseSprite.visible || !poseTextures.size) return;
  const requested = poseNameForAction(t);
  const availableForms = [...new Set([...poseTextures.keys()].map(key => key.split(":", 1)[0]))];
  const requestedForm = availableForms.includes(form)
    ? form
    : availableForms.includes("civilian")
    ? "civilian"
    : availableForms[0];
  const requestedKey = `${requestedForm}:${requested}`;
  const neutralKey = `${requestedForm}:neutral`;
  const key = poseTextures.has(requestedKey)
    ? requestedKey
    : poseTextures.has(neutralKey)
    ? neutralKey
    : [...poseTextures.keys()][0];
  const texture = poseTextures.get(key);
  if (!texture) {
    poseSprite.visible = false;
    avatar.visible = true;
    return;
  }
  if (key === currentPoseKey && poseMaterial.map === texture) return;
  currentPoseKey = key;
  poseMaterial.map = texture;
  poseMaterial.needsUpdate = true;
  const image = texture.image;
  const height = embeddedMode ? 3.5 : 3.35;
  const aspect = image?.width && image?.height ? image.width / image.height : 0.55;
  poseSprite.scale.set(height * aspect, height, 1);
}
const hips = new THREE.Group(); hips.position.y = 1.78; avatar.add(hips);
mats.pants = new THREE.MeshStandardMaterial({ color: palette.civilian.pants, roughness: 0.72 });
mats.top = new THREE.MeshStandardMaterial({ color: palette.civilian.top, roughness: 0.72 });
mats.accent = new THREE.MeshStandardMaterial({ color: palette.civilian.accent, roughness: 0.6 });
mesh(new THREE.CapsuleGeometry(0.35, 0.48, 6, 14), mats.pants, hips, 0.05).scale.set(1.1, 1, 0.78);
const torso = new THREE.Group(); torso.position.y = 0.45; hips.add(torso);
mesh(new THREE.CapsuleGeometry(0.43, 0.76, 8, 16), mats.top, torso, 0.42).scale.set(1.12, 1, 0.72);
const neck = new THREE.Group(); neck.position.y = 1.02; torso.add(neck);
mesh(new THREE.CylinderGeometry(0.14,0.15,0.2,12), skin, neck, 0.08);
const head = mesh(new THREE.SphereGeometry(0.34, 24, 18), skin, neck, 0.48); head.scale.set(0.88, 1.08, 0.92);
const hairCap = mesh(new THREE.SphereGeometry(0.36, 22, 14, 0, Math.PI*2, 0, Math.PI*0.64), hair, neck, 0.55); hairCap.scale.set(0.92,1.05,0.96);
const eyeWhiteMat = new THREE.MeshBasicMaterial({ color: 0xf7fbff });
const irisMat = new THREE.MeshBasicMaterial({ color: candidateId.includes("kara") ? 0x4b85b8 : 0x36a9c8 });
const pupilMat = new THREE.MeshBasicMaterial({ color: 0x071018 });
const browMat = new THREE.MeshStandardMaterial({ color: 0x1b2133, roughness: 0.9 });
for (const x of [-0.115,0.115]) {
  const sclera = mesh(new THREE.SphereGeometry(0.055,16,10), eyeWhiteMat, neck, 0.52);
  sclera.position.x = x; sclera.position.z = 0.305; sclera.scale.set(1.15, 0.82, 0.32);
  const iris = mesh(new THREE.SphereGeometry(0.026,12,8), irisMat, neck, 0.52);
  iris.position.set(x, 0.52, 0.323); iris.scale.set(1, 1, 0.2);
  const pupil = mesh(new THREE.SphereGeometry(0.013,10,6), pupilMat, neck, 0.52);
  pupil.position.set(x, 0.52, 0.333); pupil.scale.set(1, 1, 0.18);
  const brow = mesh(new THREE.BoxGeometry(0.105, 0.012, 0.012), browMat, neck, 0.625);
  brow.position.x = x; brow.position.z = 0.31; brow.rotation.z = x < 0 ? -0.12 : 0.12;
}
const mouthMat = new THREE.MeshBasicMaterial({ color: 0x4b1820 });
const lipMat = new THREE.MeshStandardMaterial({ color: 0xc96f72, roughness: 0.66 });
const mouth = mesh(new THREE.BoxGeometry(0.14, 0.018, 0.016), mouthMat, neck, 0.405);
mouth.position.z = 0.326;
const lowerLip = mesh(new THREE.BoxGeometry(0.13, 0.009, 0.012), lipMat, neck, 0.386);
lowerLip.position.z = 0.329;
const bangLocks = [];
for (let i = 0; i < 5; i++) {
  const lock = mesh(new THREE.CapsuleGeometry(0.035, 0.28, 5, 8), hair, neck, 0.73 - i * 0.018);
  lock.position.set(-0.15 + i * 0.072, 0.7 - i * 0.025, 0.275 + i * 0.01);
  lock.rotation.set(0.72 + i * 0.05, 0.12 - i * 0.06, -0.55 + i * 0.16);
  bangLocks.push(lock);
}
const pigtailLocks = [];
for (const side of [-1, 1]) {
  const tie = mesh(new THREE.SphereGeometry(0.055, 12, 8), new THREE.MeshStandardMaterial({ color: 0xd01f34, roughness: 0.45 }), neck, 0.43);
  tie.position.set(side * 0.36, 0.43, -0.06);
  const tail = mesh(new THREE.CapsuleGeometry(0.13, 0.42, 8, 14), hair, neck, 0.35);
  tail.position.set(side * 0.47, 0.35, -0.08);
  tail.rotation.z = side * 1.35;
  tail.scale.set(0.9, 1.05, 0.85);
  pigtailLocks.push(tail);
}
const leftArm = limb(0.13, 0.82, mats.top, torso); leftArm.pivot.position.set(-0.53,0.78,0);
const rightArm = limb(0.13, 0.82, mats.top, torso); rightArm.pivot.position.set(0.53,0.78,0);
const leftFore = limb(0.105,0.72,skin,leftArm.pivot); leftFore.pivot.position.y=-0.78;
const rightFore = limb(0.105,0.72,skin,rightArm.pivot); rightFore.pivot.position.y=-0.78;
function makeHand(parent, side) {
  const hand = new THREE.Group();
  parent.add(hand);
  hand.position.set(side * 0.012, -0.72, 0.02);
  const palm = mesh(new THREE.CapsuleGeometry(0.07, 0.12, 6, 10), skin, hand, 0);
  palm.rotation.z = side * 0.12;
  const fingers = [];
  for (let i = 0; i < 5; i++) {
    const pivot = new THREE.Group();
    pivot.position.set(side * (-0.055 + i * 0.028), -0.085, 0.018);
    hand.add(pivot);
    const finger = mesh(new THREE.CapsuleGeometry(i === 0 ? 0.014 : 0.012, i === 0 ? 0.105 : 0.14, 4, 8), skin, pivot, -0.07);
    finger.rotation.z = side * (i === 0 ? 0.52 : 0.08 - i * 0.025);
    fingers.push({ pivot, finger, index: i });
  }
  return { group: hand, fingers };
}
const leftHand = makeHand(leftFore.pivot, -1);
const rightHand = makeHand(rightFore.pivot, 1);
const leftLeg = limb(0.17,1.0,mats.pants,hips); leftLeg.pivot.position.set(-0.22,-0.18,0);
const rightLeg = limb(0.17,1.0,mats.pants,hips); rightLeg.pivot.position.set(0.22,-0.18,0);
const leftShin = limb(0.135,0.9,mats.pants,leftLeg.pivot); leftShin.pivot.position.y=-0.94;
const rightShin = limb(0.135,0.9,mats.pants,rightLeg.pivot); rightShin.pivot.position.y=-0.94;
const book = new THREE.Group();
const coverMat = new THREE.MeshStandardMaterial({ color: 0x8d3440, roughness: 0.8 });
const pageMat = new THREE.MeshStandardMaterial({ color: 0xf0e6cb, roughness: 1 });
const b1=mesh(new THREE.BoxGeometry(0.42,0.035,0.58),coverMat,book); b1.rotation.y=-0.35; b1.position.x=-0.2;
const b2=mesh(new THREE.BoxGeometry(0.42,0.035,0.58),pageMat,book); b2.rotation.y=0.35; b2.position.x=0.2;
book.visible=false; avatar.add(book);

let action = "idle", form = "civilian", actionStart = performance.now();
const clock = new THREE.Clock();
function setForm(next) {
  const aliases = {
    kara: "civilian",
    marinette: "civilian",
    default: "civilian",
    supergirl: "hero",
    ladybug: "hero",
    pajamas: "sleepwear",
    pyjamas: "sleepwear",
  };
  const normalized = aliases[String(next || "").toLowerCase()] || String(next || "").toLowerCase();
  form = palette[normalized] ? normalized : "civilian";
  mats.top.color.setHex(palette[form].top); mats.pants.color.setHex(palette[form].pants); mats.accent.color.setHex(palette[form].accent);
  applyRiggedForm(form);
  currentPoseKey = "";
  document.querySelectorAll("[data-form]").forEach(b => b.classList.toggle("active", b.dataset.form === form));
}
function setAction(next, label = "") {
  action = next || "idle"; actionStart = performance.now();
  document.querySelector("#activity").textContent = label || action.replaceAll("_", " ");
  document.querySelectorAll("[data-action]").forEach(b => b.classList.toggle("active", b.dataset.action === action));
  playRiggedAction(action);
}
document.querySelectorAll("[data-action]").forEach(b => b.onclick = () => setAction(b.dataset.action));
document.querySelectorAll("[data-form]").forEach(b => b.onclick = () => setForm(b.dataset.form));
setForm("civilian"); setAction("idle", "Standing naturally in the room");
document.querySelector("#status").textContent = "PROCEDURAL V1";

function setHandPose(hand, openness = 0.45) {
  for (const { pivot, index } of hand.fingers) {
    const curl = THREE.MathUtils.lerp(1.25, 0.05, openness);
    pivot.rotation.x = curl;
    pivot.rotation.z = (index - 2) * 0.035 * openness;
  }
}

function updateMouth(t, openness = 0) {
  const open = THREE.MathUtils.clamp(openness, 0, 1);
  mouth.scale.set(1 + open * 0.28, 1 + open * 2.7, 1);
  mouth.position.y = 0.405 - open * 0.012;
  lowerLip.position.y = 0.386 - open * 0.025;
  lowerLip.scale.x = 1 + open * 0.16;
}

function mouthOpenForText(elapsed) {
  const index = Math.floor(elapsed * 13) % lipSyncSampleText.length;
  const char = lipSyncSampleText[index]?.toLowerCase() || " ";
  if ("aeiouy".includes(char)) return 0.78;
  if ("bmp".includes(char)) return 0.08;
  if ("fv".includes(char)) return 0.26;
  if (char === " " || /[,.!?]/.test(char)) return 0.02;
  return 0.42;
}

function updateHairMotion(t, intensity = 1) {
  hairCap.rotation.z = Math.sin(t * 0.7) * 0.012 * intensity;
  for (let i = 0; i < bangLocks.length; i++) {
    bangLocks[i].rotation.z += Math.sin(t * 1.15 + i) * 0.012 * intensity;
  }
  for (let i = 0; i < pigtailLocks.length; i++) {
    const side = i === 0 ? -1 : 1;
    pigtailLocks[i].rotation.z = side * (1.35 + Math.sin(t * 1.4 + i) * 0.065 * intensity);
  }
}

const selfTestSequence = [
  { action: "stand", label: "Self-test: standing", duration: 4 },
  { action: "open_hand", label: "Self-test: opening hands", duration: 4 },
  { action: "close_hand", label: "Self-test: closing hands", duration: 4 },
  { action: "sit", label: "Self-test: sitting", duration: 5 },
  { action: "walk", label: "Self-test: walking", duration: 8 },
  { action: "jog", label: "Self-test: jogging for one minute", duration: 60 },
  { action: "talking", label: "Self-test: talking with timed mouth motion", duration: 8 },
  { action: "idle", label: "Self-test complete", duration: 999 },
];
let lastSelfTestAction = "";
function updateSelfTest(elapsed) {
  let remaining = elapsed;
  for (const step of selfTestSequence) {
    if (remaining <= step.duration) {
      if (lastSelfTestAction !== step.action) {
        lastSelfTestAction = step.action;
        setAction(step.action, step.label);
      }
      return;
    }
    remaining -= step.duration;
  }
}

function resetPose() {
  avatar.position.set(0, 0, 0.4);
  avatar.rotation.set(0, 0, 0);
  hips.position.y = 1.78;
  torso.rotation.set(0,0,0); head.rotation.set(0,0,0);
  for (const p of [leftArm.pivot,rightArm.pivot,leftFore.pivot,rightFore.pivot,leftLeg.pivot,rightLeg.pivot,leftShin.pivot,rightShin.pivot]) p.rotation.set(0,0,0);
  setHandPose(leftHand, 0.45);
  setHandPose(rightHand, 0.45);
  updateMouth(0, 0);
  book.visible=false; book.scale.set(1,1,1);
}
function animateAvatar(t) {
  resetPose();
  const elapsed=(performance.now()-actionStart)/1000;
  avatar.position.y = 0;
  torso.scale.y = 1 + Math.sin(t*1.6)*0.012;
  head.rotation.y = Math.sin(t*0.38)*0.10; head.rotation.x = Math.sin(t*0.61)*0.025;
  updateHairMotion(t, action === "jog" ? 1.9 : action === "walk" ? 1.35 : 1);
  if (action === "walk" || action === "jog") {
    const rate = action === "jog" ? 8.4 : 5.3;
    const stride = action === "jog" ? 0.68 : 0.5;
    const travel = action === "jog" ? 2.8 : 2.2;
    const s=Math.sin(t*rate); leftLeg.pivot.rotation.x=s*stride; rightLeg.pivot.rotation.x=-s*stride; leftArm.pivot.rotation.x=-s*stride*0.74; rightArm.pivot.rotation.x=s*stride*0.74;
    avatar.position.x = Math.sin(elapsed*(action === "jog" ? 0.78 : 0.55))*travel; avatar.rotation.y = Math.cos(elapsed*0.55) < 0 ? -0.25 : 0.25;
    torso.rotation.x = action === "jog" ? -0.06 : 0;
    setHandPose(leftHand, action === "jog" ? 0.24 : 0.36);
    setHandPose(rightHand, action === "jog" ? 0.24 : 0.36);
  } else if (action === "wave") {
    rightArm.pivot.rotation.z=-1.9; rightArm.pivot.rotation.x=-0.2; rightFore.pivot.rotation.z=-0.35+Math.sin(t*6)*0.35; head.rotation.y=-0.18;
    setHandPose(rightHand, 1);
    if (elapsed > 4.5) setAction("idle", "Finished waving");
  } else if (action === "open_hand" || action === "close_hand") {
    const openness = action === "open_hand" ? 1 : 0.02;
    leftArm.pivot.rotation.z = 0.92;
    rightArm.pivot.rotation.z = -0.92;
    leftArm.pivot.rotation.x = -0.45;
    rightArm.pivot.rotation.x = -0.45;
    leftFore.pivot.rotation.x = -0.2;
    rightFore.pivot.rotation.x = -0.2;
    setHandPose(leftHand, openness);
    setHandPose(rightHand, openness);
    head.rotation.x = -0.05;
  } else if (["sit","read_book","read_magazine","use_computer"].includes(action)) {
    avatar.position.set(-2.9,0,-0.72);
    avatar.rotation.y = action === "use_computer" ? Math.PI : 0;
    hips.position.y=1.02;
    leftLeg.pivot.rotation.x=-1.34; rightLeg.pivot.rotation.x=-1.34;
    leftShin.pivot.rotation.x=1.28; rightShin.pivot.rotation.x=1.28;
    if (action === "use_computer") {
      torso.rotation.x=-0.12; leftArm.pivot.rotation.x=-1.06; rightArm.pivot.rotation.x=-1.06;
      leftFore.pivot.rotation.x=-0.58; rightFore.pivot.rotation.x=-0.58;
      leftArm.pivot.rotation.z=-0.18; rightArm.pivot.rotation.z=0.18;
      head.rotation.x=-0.06 + Math.sin(t*0.7)*0.025;
    }
    if (action === "read_book" || action === "read_magazine") {
      leftArm.pivot.rotation.x=-0.96; rightArm.pivot.rotation.x=-0.96;
      leftArm.pivot.rotation.z=-0.34; rightArm.pivot.rotation.z=0.34;
      leftFore.pivot.rotation.x=-0.34; rightFore.pivot.rotation.x=-0.34;
      book.visible=true;
      book.position.set(0,1.5,0.48);
      book.rotation.set(-0.26 + Math.sin(t*0.45)*0.018,0,0);
      book.scale.set(action === "read_magazine" ? 1.28 : 1, 1, action === "read_magazine" ? 1.18 : 1);
      head.rotation.x=0.22 + Math.sin(t*0.38)*0.018;
    }
  } else if (action === "talking") {
    rightArm.pivot.rotation.z = -0.28 + Math.sin(t * 2.4) * 0.08;
    leftArm.pivot.rotation.z = 0.18 + Math.sin(t * 1.9) * 0.06;
    rightFore.pivot.rotation.x = -0.25 + Math.sin(t * 2.1) * 0.08;
    setHandPose(leftHand, 0.62);
    setHandPose(rightHand, 0.68);
    updateMouth(t, mouthOpenForText(elapsed));
  } else {
    leftArm.pivot.rotation.z=0.04+Math.sin(t*0.8)*0.02;
    rightArm.pivot.rotation.z=-0.04-Math.sin(t*0.8)*0.02;
  }
}

async function pollState() {
  try {
    const response = await fetch(`/Avatar/state/temp_ai/${encodeURIComponent(candidateId)}.json?ts=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return;
    const state = await response.json();
    const hasModel = Boolean(state.model_url);
    const hasPoseManifest = Boolean(state.pose_manifest_url);
    const shouldUseOrb = forceOrbMode || (!hasModel && !hasPoseManifest && state.model_status !== "rigged_model_ready");
    if (shouldUseOrb) showBodylessOrb("BODYLESS ORB");
    else if (hasModel) loadRiggedModel(state.model_url);
    else if (hasPoseManifest) loadPoseManifest(state.pose_manifest_url);
    if (!selfTestMode && state.action && state.action !== action) setAction(state.action, state.activity);
    if (state.form && state.form !== form) setForm(state.form);
    if (!riggedRoot && !orbGroup.visible) {
      document.querySelector("#status").textContent = poseSprite.visible
        ? "GENERATED 2D POSE"
        : state.model_status === "rigged_model_ready"
        ? "LOADING RIGGED MODEL"
        : "PROCEDURAL V1";
    }
  } catch { document.querySelector("#status").textContent = "MANUAL"; }
}
pollState();
if (!manualMode) setInterval(pollState, 2500);
else { document.querySelector("#status").textContent = "MANUAL"; }

window.__avatarRuntime = {
  candidateId,
  targetHeightMeters: AVATAR_TARGET_HEIGHT_METERS,
  handDetail: "glb_v4_visible_fingers_plus_runtime_controls",
  lipSyncMode: "glb_v4_viseme_shape_key_hooks_plus_text_timed_proxy",
  get action() { return action; },
  get form() { return form; },
  get renderedTriangles() { return renderer.info.render.triangles; },
  get modelMode() { return riggedRoot ? "rigged" : poseSprite.visible ? "generated_pose" : "procedural"; },
  get motionSample() {
    return riggedRoot ? [riggedRoot.position.y, riggedRoot.rotation.y] : null;
  },
};

function resize() { const w=innerWidth,h=innerHeight; renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix(); }
addEventListener("resize",resize); resize();
function frame() {
  requestAnimationFrame(frame);
  const delta = clock.getDelta();
  const t = clock.elapsedTime;
  if (riggedMixer) riggedMixer.update(delta);
  if (riggedRoot && !riggedClips.length) {
    riggedRoot.position.y = riggedBasePosition.y + Math.sin(t * 1.35) * 0.012;
    riggedRoot.rotation.y = riggedBaseRotationY + Math.sin(t * 0.45) * 0.015;
  }
  if (selfTestMode) updateSelfTest(t);
  if (avatar.visible) animateAvatar(t);
  if (poseSprite.visible) updatePoseSprite(t);
  if (orbGroup.visible) {
    orbGroup.position.y = 1.42 + Math.sin(t * 1.8) * 0.045;
    orbCore.scale.setScalar(1 + Math.sin(t * 2.2) * 0.035);
    orbHalo.rotation.z += delta * 0.65;
    orbHalo2.rotation.z -= delta * 0.48;
  }
  renderer.render(scene,camera);
}
frame();
