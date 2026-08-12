import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as THREE from "../Avatar/runtime3d/node_modules/three/build/three.module.js";
import { GLTFExporter } from "../Avatar/runtime3d/node_modules/three/examples/jsm/exporters/GLTFExporter.js";

globalThis.FileReader = class FileReader {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then(result => {
      this.result = result;
      this.onloadend?.({ target: this });
    });
  }

  readAsDataURL(blob) {
    blob.arrayBuffer().then(buffer => {
      this.result = `data:${blob.type || "application/octet-stream"};base64,${Buffer.from(buffer).toString("base64")}`;
      this.onloadend?.({ target: this });
    });
  }
};

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const candidateId = "ladybug_marinette_expanded_smoke";
const outputDir = path.join(root, "Avatar", "models", "temp_ai", candidateId);
const outputPath = path.join(outputDir, "avatar.glb");

const scene = new THREE.Scene();
scene.name = "Marinette_Ladybug_Turnaround_Rebuild_V3";

function material(name, color, roughness = 0.82, metalness = 0) {
  const value = new THREE.MeshStandardMaterial({
    color,
    roughness,
    metalness,
    flatShading: false,
  });
  value.name = name;
  return value;
}

const mats = {
  skin: material("warm_light_skin", 0xf3c7ad, 0.86),
  blush: material("soft_blush", 0xe89a9d, 0.82),
  hair: material("marinette_blue_black_hair", 0x101d3b, 0.72),
  hairLight: material("marinette_hair_highlight", 0x243963, 0.68),
  eyeWhite: material("eye_white", 0xfffdf7, 0.55),
  iris: material("marinette_blue_iris", 0x41a5ca, 0.48),
  pupil: material("pupil", 0x07101d, 0.52),
  lash: material("lashes", 0x10131d, 0.65),
  mouth: material("rose_mouth", 0xb95765, 0.76),
  jacket: material("charcoal_cropped_jacket", 0x222a39, 0.84),
  shirt: material("warm_gray_shirt", 0xe8e5dc, 0.86),
  pink: material("marinette_rose_pants", 0xe7677e, 0.80),
  red: material("ladybug_suit_red", 0xd8203d, 0.67),
  spot: material("ladybug_spots", 0x101217, 0.60),
  shoe: material("civilian_ballet_flat", 0x282a32, 0.86),
};

function addMesh(parent, name, geometry, mat, position, scale = [1, 1, 1], rotation = [0, 0, 0]) {
  const mesh = new THREE.Mesh(geometry, mat);
  mesh.name = name;
  mesh.position.set(...position);
  mesh.scale.set(...scale);
  mesh.rotation.set(...rotation);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function sphere(parent, name, mat, position, scale) {
  return addMesh(parent, name, new THREE.SphereGeometry(1, 40, 30), mat, position, scale);
}

function faceGeometry() {
  const geometry = new THREE.SphereGeometry(1, 64, 48);
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    const x = position.getX(index);
    const y = position.getY(index);
    const z = position.getZ(index);
    let width = 1;
    if (y < -0.62) width = THREE.MathUtils.lerp(0.62, 0.84, THREE.MathUtils.smoothstep(y, -0.98, -0.62));
    else if (y < -0.02) width = THREE.MathUtils.lerp(0.84, 1.0, THREE.MathUtils.smoothstep(y, -0.62, -0.02));
    else if (y > 0.64) width = THREE.MathUtils.lerp(1.0, 0.94, THREE.MathUtils.smoothstep(y, 0.64, 1.0));
    const cheek = 1 + 0.035 * Math.exp(-Math.pow((y + 0.18) / 0.26, 2));
    const front = z > 0 ? 1 + 0.035 * Math.exp(-Math.pow((y + 0.05) / 0.55, 2)) : 0.98;
    position.setXYZ(index, x * width * cheek, y, z * front);
  }
  geometry.computeVertexNormals();
  return geometry;
}

function sectionGeometry(sections, radialSegments = 36) {
  const vertices = [];
  const indices = [];
  for (const section of sections) {
    for (let radial = 0; radial < radialSegments; radial += 1) {
      const angle = radial / radialSegments * Math.PI * 2;
      vertices.push(
        (section.x || 0) + Math.cos(angle) * section.rx,
        section.y,
        (section.z || 0) + Math.sin(angle) * section.rz,
      );
    }
  }
  for (let ring = 0; ring < sections.length - 1; ring += 1) {
    for (let radial = 0; radial < radialSegments; radial += 1) {
      const next = (radial + 1) % radialSegments;
      const a = ring * radialSegments + radial;
      const b = ring * radialSegments + next;
      const c = (ring + 1) * radialSegments + radial;
      const d = (ring + 1) * radialSegments + next;
      indices.push(a, c, b, b, c, d);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function sectionMesh(parent, name, mat, sections, radialSegments = 36) {
  return addMesh(parent, name, sectionGeometry(sections, radialSegments), mat, [0, 0, 0]);
}

function almondGeometry(width, height) {
  const shape = new THREE.Shape();
  shape.moveTo(-width / 2, 0);
  shape.bezierCurveTo(-width * 0.28, height * 0.62, width * 0.28, height * 0.62, width / 2, 0);
  shape.bezierCurveTo(width * 0.28, -height * 0.48, -width * 0.28, -height * 0.48, -width / 2, 0);
  return new THREE.ShapeGeometry(shape, 32);
}

function curveLine(parent, name, mat, points, radius = 0.008) {
  const curve = new THREE.CatmullRomCurve3(points.map(point => new THREE.Vector3(...point)));
  return addMesh(parent, name, new THREE.TubeGeometry(curve, 24, radius, 8, false), mat, [0, 0, 0]);
}

function capsule(parent, name, radius, totalLength, mat, position, rotation = [0, 0, 0], scale = [1, 1, 1]) {
  return addMesh(
    parent,
    name,
    new THREE.CapsuleGeometry(radius, Math.max(0.01, totalLength - radius * 2), 12, 24),
    mat,
    position,
    scale,
    rotation,
  );
}

function disc(parent, name, mat, position, scale, rotation = [0, 0, 0]) {
  return addMesh(parent, name, new THREE.CircleGeometry(1, 36), mat, position, scale, rotation);
}

function taperedLimb(parent, name, topRadius, bottomRadius, length, mat, position, rotation = [0, 0, 0], scale = [1, 1, 1]) {
  return addMesh(
    parent,
    name,
    new THREE.CylinderGeometry(topRadius, bottomRadius, length, 28, 3, false),
    mat,
    position,
    scale,
    rotation,
  );
}

const body = new THREE.Group();
body.name = "Marinette_Ladybug_Body";
scene.add(body);

// Shared head. A deformed single face mesh replaces the detached ball-and-chin
// construction. Proportions follow the supplied front, side, and three-quarter
// turnarounds: tapered jaw, broad upper face, low pigtails, and swept fringe.
addMesh(body, "shared_face", faceGeometry(), mats.skin, [0, 3.12, 0.025], [0.305, 0.355, 0.235]);
sphere(body, "shared_left_ear", mats.skin, [-0.292, 3.13, -0.005], [0.030, 0.061, 0.027]);
sphere(body, "shared_right_ear", mats.skin, [0.292, 3.13, -0.005], [0.030, 0.061, 0.027]);
sphere(body, "shared_hair_back", mats.hair, [0, 3.19, -0.098], [0.315, 0.369, 0.220]);
sphere(body, "shared_hair_crown", mats.hair, [0, 3.405, -0.010], [0.306, 0.158, 0.214]);

for (const side of [-1, 1]) {
  const sideName = side < 0 ? "left" : "right";
  sphere(body, `shared_${sideName}_pigtail_upper`, mats.hair,
    [side * 0.355, 2.995, -0.072], [0.133, 0.111, 0.110]);
  sphere(body, `shared_${sideName}_pigtail_lower`, mats.hairLight,
    [side * 0.368, 2.875, -0.078], [0.156, 0.145, 0.130]);
  addMesh(body, `shared_${sideName}_red_hair_tie`, new THREE.TorusGeometry(0.046, 0.012, 10, 26), mats.red,
    [side * 0.316, 3.055, -0.035], [1.08, 1.08, 1.08], [Math.PI / 2, 0, 0]);
  curveLine(body, `shared_${sideName}_side_lock`, mats.hair, [
    [side * 0.246, 3.37, 0.156], [side * 0.282, 3.20, 0.204], [side * 0.254, 3.01, 0.207],
  ], 0.018);
}

// Smooth overlapping locks keep the swept fringe readable without the rigid
// cone silhouette that made the first procedural pass look like a helmet.
const fringe = [
  [-0.224, 3.405, 0.198, -0.43, 0.082, 0.158],
  [-0.130, 3.425, 0.224, -0.28, 0.095, 0.178],
  [-0.024, 3.425, 0.239, -0.10, 0.098, 0.188],
  [0.086, 3.397, 0.231, 0.18, 0.094, 0.178],
  [0.194, 3.348, 0.202, 0.42, 0.080, 0.153],
];
for (const [x, y, z, angle, width, length] of fringe) {
  sphere(body, `shared_fringe_${x}`, mats.hair, [x, y, z], [width, length, 0.052])
    .rotation.z = angle;
}

for (const side of [-1, 1]) {
  const sideName = side < 0 ? "left" : "right";
  addMesh(body, `shared_${sideName}_eye_white`, almondGeometry(0.166, 0.116), mats.eyeWhite,
    [side * 0.112, 3.150, 0.258]);
  sphere(body, `shared_${sideName}_iris`, mats.iris, [side * 0.112, 3.150, 0.266], [0.037, 0.048, 0.011]);
  sphere(body, `shared_${sideName}_pupil`, mats.pupil, [side * 0.112, 3.150, 0.275], [0.014, 0.026, 0.008]);
  sphere(body, `shared_${sideName}_eye_glint`, mats.eyeWhite, [side * 0.100, 3.171, 0.282], [0.007, 0.009, 0.004]);
  curveLine(body, `shared_${sideName}_upper_lash`, mats.lash, [
    [side * 0.197, 3.156, 0.267], [side * 0.112, 3.203, 0.278], [side * 0.027, 3.158, 0.267],
  ], 0.0065);
  curveLine(body, `shared_${sideName}_brow`, mats.hair, [
    [side * 0.195, 3.260, 0.245], [side * 0.120, 3.283, 0.260], [side * 0.040, 3.262, 0.254],
  ], 0.007);
}

sphere(body, "shared_nose", mats.skin, [0, 3.070, 0.275], [0.016, 0.026, 0.012]);
curveLine(body, "shared_mouth", mats.mouth, [[-0.054, 2.982, 0.266], [0, 2.968, 0.272], [0.054, 2.982, 0.266]], 0.006);
sphere(body, "shared_left_blush", mats.blush, [-0.177, 3.045, 0.240], [0.047, 0.013, 0.007]);
sphere(body, "shared_right_blush", mats.blush, [0.177, 3.045, 0.240], [0.047, 0.013, 0.007]);
capsule(body, "shared_neck", 0.062, 0.22, mats.skin, [0, 2.77, 0], [0, 0, 0], [1, 1, 0.86]);

function buildForm(prefix, hero) {
  const group = new THREE.Group();
  group.name = `${prefix}_form_group`;
  body.add(group);

  const torsoMat = hero ? mats.red : mats.shirt;
  const armMat = hero ? mats.red : mats.skin;
  const legMat = hero ? mats.red : mats.pink;

  // One connected torso/hip surface and one connected surface per limb. This
  // removes the detached doll joints while retaining the reference silhouette.
  sectionMesh(group, `${prefix}_torso_hips`, torsoMat, [
    { y: 2.71, rx: 0.105, rz: 0.085 },
    { y: 2.65, rx: 0.220, rz: 0.125 },
    { y: 2.52, rx: 0.229, rz: 0.140 },
    { y: 2.30, rx: 0.194, rz: 0.132 },
    { y: 2.04, rx: 0.166, rz: 0.122 },
    { y: 1.88, rx: 0.183, rz: 0.133 },
    { y: 1.72, rx: 0.239, rz: 0.159 },
    { y: 1.65, rx: 0.220, rz: 0.149 },
  ]);

  for (const side of [-1, 1]) {
    const sideName = side < 0 ? "left" : "right";
    sectionMesh(group, `${prefix}_${sideName}_arm`, hero ? mats.red : mats.jacket, [
      { x: side * 0.192, y: 2.61, rx: 0.076, rz: 0.073 },
      { x: side * 0.258, y: 2.47, rx: 0.073, rz: 0.070 },
      { x: side * 0.307, y: 2.22, rx: 0.061, rz: 0.059 },
      { x: side * 0.345, y: 1.98, rx: 0.056, rz: 0.053 },
      { x: side * 0.369, y: 1.73, rx: 0.047, rz: 0.044 },
    ], 28);
    if (!hero) {
      sectionMesh(group, `${prefix}_${sideName}_forearm_skin`, mats.skin, [
        { x: side * 0.345, y: 2.03, rx: 0.056, rz: 0.053 },
        { x: side * 0.369, y: 1.73, rx: 0.047, rz: 0.044 },
      ], 28);
    }
    sphere(group, `${prefix}_${sideName}_hand`, armMat, [side * 0.377, 1.645, 0.012], [0.052, 0.070, 0.036]);
    sphere(group, `${prefix}_${sideName}_thumb`, armMat, [side * 0.420, 1.656, 0.026], [0.019, 0.041, 0.018]);

    sectionMesh(group, `${prefix}_${sideName}_leg`, legMat, [
      { x: side * 0.105, y: 1.70, rx: 0.108, rz: 0.128 },
      { x: side * 0.105, y: 1.50, rx: 0.098, rz: 0.112 },
      { x: side * 0.105, y: 1.16, rx: 0.079, rz: 0.089 },
      { x: side * 0.105, y: 0.92, rx: 0.069, rz: 0.076 },
      { x: side * 0.105, y: 0.68, rx: 0.064, rz: 0.069 },
      { x: side * 0.105, y: 0.35, rx: 0.050, rz: 0.055 },
      { x: side * 0.105, y: 0.23, rx: 0.047, rz: 0.051 },
    ], 32);
    if (!hero) capsule(group, `${prefix}_${sideName}_ankle`, 0.042, 0.24, mats.skin, [side * 0.105, 0.16, 0]);
    sphere(group, `${prefix}_${sideName}_shoe`, hero ? mats.red : mats.shoe,
      [side * 0.105, 0.055, 0.060], [0.071, 0.040, 0.135]);
  }

  if (!hero) {
    // Marinette's familiar cropped charcoal jacket and pale flower-print tee.
    sectionMesh(group, `${prefix}_jacket_shell`, mats.jacket, [
      { y: 2.67, rx: 0.246, rz: 0.136 },
      { y: 2.54, rx: 0.258, rz: 0.148 },
      { y: 2.30, rx: 0.216, rz: 0.142 },
      { y: 2.08, rx: 0.181, rz: 0.132 },
    ]);
    addMesh(group, `${prefix}_shirt_front`, new THREE.PlaneGeometry(0.245, 0.58), mats.shirt,
      [0, 2.38, 0.151]);
    addMesh(group, `${prefix}_jacket_left_lapel`, new THREE.BoxGeometry(0.092, 0.56, 0.026), mats.jacket,
      [-0.150, 2.38, 0.165], [1, 1, 1], [0, 0, -0.08]);
    addMesh(group, `${prefix}_jacket_right_lapel`, new THREE.BoxGeometry(0.092, 0.56, 0.026), mats.jacket,
      [0.150, 2.38, 0.165], [1, 1, 1], [0, 0, 0.08]);
    sphere(group, `${prefix}_shirt_flower_center`, mats.pink, [0, 2.45, 0.170], [0.031, 0.023, 0.010]);
    for (let index = 0; index < 5; index += 1) {
      const angle = index * Math.PI * 0.4;
      sphere(group, `${prefix}_shirt_flower_petal_${index}`, mats.blush,
        [Math.cos(angle) * 0.040, 2.45 + Math.sin(angle) * 0.032, 0.169], [0.023, 0.015, 0.007]);
    }
  } else {
    // Red eye mask follows the face and leaves the shared eyes visible.
    for (const side of [-1, 1]) {
      disc(group, `${prefix}_${side < 0 ? "left" : "right"}_mask_lobe`, mats.red,
        [side * 0.092, 3.105, 0.201], [0.105, 0.073, 1]);
    }
    disc(group, `${prefix}_mask_bridge`, mats.red, [0, 3.11, 0.202], [0.075, 0.035, 1]);
    const spots = [
      [-0.13, 2.55, 0.18], [0.14, 2.41, 0.18], [-0.08, 2.18, 0.18], [0.12, 1.91, 0.16],
      [-0.31, 2.34, 0.06], [0.31, 2.10, 0.06], [-0.13, 1.35, 0.10], [0.13, 0.86, 0.09],
    ];
    spots.forEach(([x, y, z], index) => {
      sphere(group, `${prefix}_spot_${index + 1}`, mats.spot, [x, y, z], [0.038, 0.038, 0.014]);
    });
  }
}

buildForm("civilian", false);
buildForm("hero", true);

const exporter = new GLTFExporter();
const glb = await exporter.parseAsync(scene, { binary: true, onlyVisible: false, trs: true });
await fs.mkdir(outputDir, { recursive: true });
await fs.writeFile(outputPath, Buffer.from(glb));
console.log(outputPath);
