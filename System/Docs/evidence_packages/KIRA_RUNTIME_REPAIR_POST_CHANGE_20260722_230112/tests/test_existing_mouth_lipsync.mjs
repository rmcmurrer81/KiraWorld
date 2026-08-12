import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  createExistingMouthLipSyncRig,
  findExistingMouthVertexRegion,
  restoreExistingMouthLipSyncRig,
  updateExistingMouthLipSyncRig,
} from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/existing_mouth_lipsync.js";

class Attribute {
  constructor(array, itemSize = 3) {
    this.array = array;
    this.itemSize = itemSize;
    this.count = array.length / itemSize;
    this.needsUpdate = false;
  }
  getX(index) { return this.array[index * this.itemSize]; }
  getY(index) { return this.array[index * this.itemSize + 1]; }
  getZ(index) { return this.array[index * this.itemSize + 2]; }
  setX(index, value) { this.array[index * this.itemSize] = value; }
  setY(index, value) { this.array[index * this.itemSize + 1] = value; }
  setZ(index, value) { this.array[index * this.itemSize + 2] = value; }
  clone() { return new Attribute(new this.array.constructor(this.array), this.itemSize); }
}

function fixture() {
  const vertices = [
    -0.4, -0.09, 0, 0.4, -0.09, 0, 0.4, 0.08, 0, -0.4, 0.08, 0,
    -0.4, -0.09, 1.18, 0.4, -0.09, 1.18, 0.4, 0.08, 1.18, -0.4, 0.08, 1.18,
  ];
  const indices = [
    0, 1, 2, 0, 2, 3, 4, 6, 5, 4, 7, 6,
    0, 4, 5, 0, 5, 1, 1, 5, 6, 1, 6, 2,
    2, 6, 7, 2, 7, 3, 3, 7, 4, 3, 4, 0,
  ];
  const mouthStart = vertices.length / 3;
  const count = 60;
  for (let index = 0; index < count; index += 1) {
    const angle = (index / count) * Math.PI * 2;
    vertices.push(
      Math.cos(angle) * 0.0144,
      -0.056 + Math.sin(angle * 2) * 0.005,
      1.05256 + Math.sin(angle) * 0.002655,
    );
  }
  for (let index = 1; index < count - 1; index += 1) {
    indices.push(mouthStart, mouthStart + index, mouthStart + index + 1);
  }
  // An existing centre-seam vertex gives the synthetic fixture both a fixed
  // outer lip perimeter and an interior seam, matching the authored R6 island.
  const seamVertex = vertices.length / 3;
  vertices.push(0, -0.056, 1.05256);
  for (let index = 0; index < count; index += 1) {
    indices.push(seamVertex, mouthStart + index, mouthStart + ((index + 1) % count));
  }
  return {
    position: new Attribute(new Float32Array(vertices)),
    index: new Attribute(new Uint32Array(indices), 1),
    mouthStart,
    mouthCount: count + 1,
    seamVertex,
  };
}

test("selects only the existing connected lip island and restores it exactly", () => {
  const { position, index, mouthStart, mouthCount, seamVertex } = fixture();
  const before = new Float32Array(position.array);
  const region = findExistingMouthVertexRegion(position, index);
  assert.ok(region);
  assert.equal(region.vertices.length, mouthCount);
  assert.equal(Math.min(...region.vertices), mouthStart);

  const material = {
    vertexColors: false,
    clone() { return { ...this, clone: this.clone, dispose() { this.disposed = true; } }; },
  };
  const geometry = {
    attributes: { position },
    setAttribute(name, attribute) { this.attributes[name] = attribute; },
    deleteAttribute(name) { delete this.attributes[name]; },
  };
  const mesh = { name: "existing_skinned_body", geometry, material };
  const rig = createExistingMouthLipSyncRig(mesh, region);
  assert.ok(rig);
  assert.equal(rig.createdSceneNodes, 0);
  assert.equal(rig.existingVertexColorSpeechShading, true);
  assert.equal(mesh.material.vertexColors, true);
  updateExistingMouthLipSyncRig(rig, { playing: true, seconds: 1.3, deltaSeconds: 0.1 });
  assert.ok(rig.amount > 0);
  assert.ok(rig.targetAmount >= 0.32, "confirmed playback keeps a readable speech floor");
  assert.ok(
    rig.openingDistance >= 0.0045,
    "synthetic fixture should reach the configured deformation-distance floor",
  );
  assert.ok(rig.maximumOpeningDistance <= 0.010, "speech aperture must remain within its 10 mm hard cap");
  assert.ok(rig.maximumSeamDisplacement > 0.001, "the existing centre seam should move");
  assert.ok(rig.maximumPerimeterDisplacement < 0.00001, "the outer lip perimeter must remain anchored");
  assert.ok(rig.innerLipShadeAmount > 0);
  assert.ok(
    region.vertices.some((vertex) => geometry.attributes.color.getY(vertex) < 0.9),
    "existing lip vertices should visibly darken near the speaking seam",
  );
  assert.ok(
    Math.abs(position.getZ(seamVertex) - before[seamVertex * 3 + 2]) > 0.001,
    "the authored centre seam should open",
  );
  assert.ok(
    region.vertices.some((vertex) => geometry.attributes.color.getY(vertex) > 0.99),
    "outer existing lip vertices should keep their original colour",
  );

  for (let index = 0; index < mouthStart * 3; index += 1) {
    assert.equal(position.array[index], before[index], `non-mouth coordinate ${index} moved`);
  }
  assert.notDeepEqual(
    [...position.array.slice(mouthStart * 3)],
    [...before.slice(mouthStart * 3)],
  );

  assert.equal(restoreExistingMouthLipSyncRig(rig), true);
  assert.deepEqual([...position.array], [...before]);
  assert.equal(geometry.attributes.color, undefined);
  assert.equal(mesh.material, material);
});

test("implementation cannot instantiate a second Three.js mouth mesh", async () => {
  const source = await readFile(new URL(
    "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/existing_mouth_lipsync.js",
    import.meta.url,
  ), "utf8");
  assert.equal(source.includes("new THREE.Mesh"), false);
  assert.equal(source.includes("new Mesh("), false);
  assert.match(source, /existing[_ ]position[_ ]attribute/i);
});

test("ambient smile moves only the existing lip island and yields to speech", () => {
  const { position, index, mouthStart } = fixture();
  const before = new Float32Array(position.array);
  const region = findExistingMouthVertexRegion(position, index);
  const material = {
    vertexColors: false,
    clone() { return { ...this, clone: this.clone, dispose() {} }; },
  };
  const geometry = {
    attributes: { position },
    setAttribute(name, attribute) { this.attributes[name] = attribute; },
    deleteAttribute(name) { delete this.attributes[name]; },
  };
  const rig = createExistingMouthLipSyncRig({ name: "existing_skinned_body", geometry, material }, region);
  updateExistingMouthLipSyncRig(rig, { playing: false, seconds: 9, deltaSeconds: 1, smileAmount: 0.2 });
  assert.ok(rig.smileAmount > 0.19);
  assert.equal(rig.amount, 0);
  for (let coordinate = 0; coordinate < mouthStart * 3; coordinate += 1) {
    assert.equal(position.array[coordinate], before[coordinate]);
  }
  assert.notDeepEqual([...position.array], [...before]);

  updateExistingMouthLipSyncRig(rig, { playing: true, seconds: 9.1, deltaSeconds: 1, smileAmount: 0.2 });
  assert.equal(rig.targetSmileAmount, 0);
  assert.ok(rig.smileAmount < 0.001);
  assert.ok(rig.amount > 0);
  assert.equal(rig.createdSceneNodes, 0);
  assert.equal(restoreExistingMouthLipSyncRig(rig), true);
  assert.deepEqual([...position.array], [...before]);
});
