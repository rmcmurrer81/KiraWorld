export const KIRA_EXISTING_MOUTH_LIPSYNC_VERSION = "existing-lip-island-audio-playback-v8-readable-bounded-anchored-seam";

const EPSILON = 1e-9;

function attributeCount(attribute) {
  if (Number.isFinite(attribute?.count)) return Number(attribute.count);
  const itemSize = Number(attribute?.itemSize || 3);
  return Math.floor((attribute?.array?.length || 0) / itemSize);
}

function attributeValue(attribute, index, axis) {
  const getter = axis === 0 ? "getX" : axis === 1 ? "getY" : "getZ";
  if (typeof attribute?.[getter] === "function") return Number(attribute[getter](index));
  const itemSize = Number(attribute?.itemSize || 3);
  return Number(attribute?.array?.[index * itemSize + axis] || 0);
}

function setAttributeValue(attribute, index, axis, value) {
  const setter = axis === 0 ? "setX" : axis === 1 ? "setY" : "setZ";
  if (typeof attribute?.[setter] === "function") {
    attribute[setter](index, value);
    return;
  }
  const itemSize = Number(attribute?.itemSize || 3);
  attribute.array[index * itemSize + axis] = value;
}

function indexCount(attribute) {
  if (Number.isFinite(attribute?.count)) return Number(attribute.count);
  return attribute?.array?.length || 0;
}

function indexValue(attribute, index) {
  if (typeof attribute?.getX === "function") return Number(attribute.getX(index));
  return Number(attribute?.array?.[index] || 0);
}

function axisBounds(position, vertices = null) {
  const count = vertices ? vertices.length : attributeCount(position);
  const low = [Infinity, Infinity, Infinity];
  const high = [-Infinity, -Infinity, -Infinity];
  for (let offset = 0; offset < count; offset += 1) {
    const vertex = vertices ? vertices[offset] : offset;
    for (let axis = 0; axis < 3; axis += 1) {
      const value = attributeValue(position, vertex, axis);
      low[axis] = Math.min(low[axis], value);
      high[axis] = Math.max(high[axis], value);
    }
  }
  return {
    low,
    high,
    center: low.map((value, axis) => (value + high[axis]) * 0.5),
    size: low.map((value, axis) => high[axis] - value),
  };
}

function unionFind(size) {
  const parent = new Int32Array(size);
  const rank = new Uint8Array(size);
  for (let index = 0; index < size; index += 1) parent[index] = index;
  const find = (value) => {
    let root = value;
    while (parent[root] !== root) root = parent[root];
    while (parent[value] !== value) {
      const next = parent[value];
      parent[value] = root;
      value = next;
    }
    return root;
  };
  const unite = (left, right) => {
    let leftRoot = find(left);
    let rightRoot = find(right);
    if (leftRoot === rightRoot) return;
    if (rank[leftRoot] < rank[rightRoot]) [leftRoot, rightRoot] = [rightRoot, leftRoot];
    parent[rightRoot] = leftRoot;
    if (rank[leftRoot] === rank[rightRoot]) rank[leftRoot] += 1;
  };
  return { find, unite };
}

function connectedComponents(position, index) {
  const vertexCount = attributeCount(position);
  if (!index || indexCount(index) < 3 || vertexCount < 3) return [];
  const components = unionFind(vertexCount);
  const count = indexCount(index) - (indexCount(index) % 3);
  for (let cursor = 0; cursor < count; cursor += 3) {
    const a = indexValue(index, cursor);
    const b = indexValue(index, cursor + 1);
    const c = indexValue(index, cursor + 2);
    if (a < 0 || b < 0 || c < 0 || a >= vertexCount || b >= vertexCount || c >= vertexCount) continue;
    components.unite(a, b);
    components.unite(b, c);
  }
  const byRoot = new Map();
  for (let vertex = 0; vertex < vertexCount; vertex += 1) {
    const root = components.find(vertex);
    if (!byRoot.has(root)) byRoot.set(root, []);
    byRoot.get(root).push(vertex);
  }
  return [...byRoot.values()];
}

function semanticBodyAxes(full) {
  const ranked = full.size
    .map((size, axis) => ({ axis, size: Math.abs(size) }))
    .sort((left, right) => left.size - right.size);
  return {
    depthAxis: ranked[0].axis,
    horizontalAxis: ranked[1].axis,
    verticalAxis: ranked[2].axis,
  };
}

function mouthCandidateScore(stats, full, axes) {
  const range = full.size.map((value) => Math.max(Math.abs(value), EPSILON));
  const semanticOrder = [axes.horizontalAxis, axes.depthAxis, axes.verticalAxis];
  const normalizedCenter = semanticOrder.map((axis) => (stats.center[axis] - full.low[axis]) / range[axis]);
  const normalizedSize = semanticOrder.map((axis) => stats.size[axis] / range[axis]);
  const centered = Math.abs(normalizedCenter[0] - 0.5);
  // Blender and glTF/Three.js may reverse the local depth axis. The same
  // existing front-face island is therefore valid near either 0.20 or 0.80.
  const faceDepth = Math.min(
    Math.abs(normalizedCenter[1] - 0.20),
    Math.abs(normalizedCenter[1] - 0.80),
  );
  const lowerFaceHeight = Math.abs(normalizedCenter[2] - 0.892);
  const lipWidth = Math.abs(normalizedSize[0] - 0.036);
  const lipHeight = Math.abs(normalizedSize[2] - 0.0045);
  return {
    score: centered * 7 + faceDepth * 5 + lowerFaceHeight * 18 + lipWidth * 7 + lipHeight * 5,
    normalizedCenter,
    normalizedSize,
  };
}

/**
 * Finds the already-authored lip island inside a single indexed body mesh.
 * It never creates geometry and refuses broad face/body selections.
 */
export function findExistingMouthVertexRegion(position, index) {
  const full = axisBounds(position);
  const axes = semanticBodyAxes(full);
  const components = connectedComponents(position, index);
  const candidates = [];
  for (const vertices of components) {
    if (vertices.length < 40 || vertices.length > 1200) continue;
    const stats = axisBounds(position, vertices);
    const scored = mouthCandidateScore(stats, full, axes);
    const [nx, ny, nz] = scored.normalizedCenter;
    const [sx, , sz] = scored.normalizedSize;
    if (nx < 0.44 || nx > 0.56) continue;
    const inForwardFaceDepthBand = (ny >= 0.02 && ny <= 0.46) || (ny >= 0.54 && ny <= 0.98);
    if (!inForwardFaceDepthBand) continue;
    if (nz < 0.84 || nz > 0.925) continue;
    if (sx < 0.012 || sx > 0.085) continue;
    if (sz < 0.001 || sz > 0.022) continue;
    candidates.push({ vertices, stats, ...scored });
  }
  candidates.sort((left, right) => left.score - right.score);
  const selected = candidates[0] || null;
  if (!selected || selected.score > 0.48) return null;
  return {
    vertices: selected.vertices,
    center: selected.stats.center,
    size: selected.stats.size,
    score: selected.score,
    normalizedCenter: selected.normalizedCenter,
    normalizedSize: selected.normalizedSize,
    fullBounds: full,
    axes,
    componentCount: components.length,
  };
}

export function auditExistingMouthVertexRegions(position, index, limit = 12) {
  const full = axisBounds(position);
  const axes = semanticBodyAxes(full);
  return connectedComponents(position, index)
    .filter((vertices) => vertices.length >= 40 && vertices.length <= 1200)
    .map((vertices) => {
      const stats = axisBounds(position, vertices);
      const scored = mouthCandidateScore(stats, full, axes);
      return {
        vertexCount: vertices.length,
        score: Number(scored.score.toFixed(6)),
        normalizedCenter: scored.normalizedCenter.map((value) => Number(value.toFixed(6))),
        normalizedSize: scored.normalizedSize.map((value) => Number(value.toFixed(6))),
      };
    })
    .sort((left, right) => left.score - right.score)
    .slice(0, Math.max(1, Number(limit) || 12));
}

export function createExistingMouthLipSyncRig(mesh, region) {
  const position = mesh?.geometry?.attributes?.position;
  if (!position || !region?.vertices?.length) return null;
  const base = new Float32Array(region.vertices.length * 3);
  region.vertices.forEach((vertex, offset) => {
    base[offset * 3] = attributeValue(position, vertex, 0);
    base[offset * 3 + 1] = attributeValue(position, vertex, 1);
    base[offset * 3 + 2] = attributeValue(position, vertex, 2);
  });
  const geometry = mesh.geometry;
  let color = geometry.attributes?.color || null;
  let createdColorAttribute = false;
  let baseColor = null;
  let originalMaterial = null;
  let speechMaterials = [];
  // The live body has an authored lip island but no dark oral cavity or facial
  // controls.  Give only those existing lip vertices a temporary vertex-color
  // seam so their separation is readable.  This does not add a mesh, a mouth,
  // or a scene node; it merely shades vertices already in the live face mesh.
  if (typeof geometry.setAttribute === "function" && typeof position.clone === "function") {
    if (!color) {
      color = position.clone();
      for (let vertex = 0; vertex < attributeCount(color); vertex += 1) {
        setAttributeValue(color, vertex, 0, 1);
        setAttributeValue(color, vertex, 1, 1);
        setAttributeValue(color, vertex, 2, 1);
      }
      geometry.setAttribute("color", color);
      createdColorAttribute = true;
    }
    baseColor = new Float32Array(region.vertices.length * 3);
    region.vertices.forEach((vertex, offset) => {
      baseColor[offset * 3] = attributeValue(color, vertex, 0);
      baseColor[offset * 3 + 1] = attributeValue(color, vertex, 1);
      baseColor[offset * 3 + 2] = attributeValue(color, vertex, 2);
    });
    originalMaterial = mesh.material;
    const originalMaterials = Array.isArray(originalMaterial) ? originalMaterial : [originalMaterial];
    speechMaterials = originalMaterials
      .map((material) => {
        if (!material?.clone) return material;
        const clone = material.clone();
        clone.vertexColors = true;
        clone.needsUpdate = true;
        return clone;
      });
    mesh.material = Array.isArray(originalMaterial) ? speechMaterials : speechMaterials[0];
  }
  return {
    version: KIRA_EXISTING_MOUTH_LIPSYNC_VERSION,
    mesh,
    position,
    region,
    base,
    color,
    baseColor,
    createdColorAttribute,
    originalMaterial,
    originalMaterials: Array.isArray(originalMaterial) ? originalMaterial : [originalMaterial],
    speechMaterials,
    amount: 0,
    targetAmount: 0,
    smileAmount: 0,
    targetSmileAmount: 0,
    peakSmileAmount: 0,
    restored: true,
    updateCount: 0,
    peakAmount: 0,
    openingDistance: 0,
    maximumOpeningDistance: 0,
    maximumAppliedDisplacement: 0,
    maximumSeamDisplacement: 0,
    maximumPerimeterDisplacement: 0,
    innerLipShadeAmount: 0,
    existingVertexColorSpeechShading: !!color && !!baseColor,
    createdSceneNodes: 0,
  };
}

export function restoreExistingMouthLipSyncRig(rig) {
  if (!rig?.position || !rig?.region?.vertices) return false;
  rig.region.vertices.forEach((vertex, offset) => {
    setAttributeValue(rig.position, vertex, 0, rig.base[offset * 3]);
    setAttributeValue(rig.position, vertex, 1, rig.base[offset * 3 + 1]);
    setAttributeValue(rig.position, vertex, 2, rig.base[offset * 3 + 2]);
  });
  rig.position.needsUpdate = true;
  if (rig.color && rig.baseColor) {
    rig.region.vertices.forEach((vertex, offset) => {
      setAttributeValue(rig.color, vertex, 0, rig.baseColor[offset * 3]);
      setAttributeValue(rig.color, vertex, 1, rig.baseColor[offset * 3 + 1]);
      setAttributeValue(rig.color, vertex, 2, rig.baseColor[offset * 3 + 2]);
    });
    rig.color.needsUpdate = true;
  }
  if (rig.originalMaterial) {
    rig.mesh.material = rig.originalMaterial;
    for (const material of rig.speechMaterials || []) {
      if (material && !(rig.originalMaterials || []).includes(material) && typeof material.dispose === "function") material.dispose();
    }
  }
  if (rig.createdColorAttribute && typeof rig.mesh?.geometry?.deleteAttribute === "function") {
    rig.mesh.geometry.deleteAttribute("color");
    rig.color = null;
  }
  rig.amount = 0;
  rig.targetAmount = 0;
  rig.smileAmount = 0;
  rig.targetSmileAmount = 0;
  rig.openingDistance = 0;
  rig.maximumAppliedDisplacement = 0;
  rig.maximumSeamDisplacement = 0;
  rig.maximumPerimeterDisplacement = 0;
  rig.innerLipShadeAmount = 0;
  rig.restored = true;
  return true;
}

function speechPulse(seconds) {
  const fast = Math.abs(Math.sin(seconds * 11.7));
  const medium = Math.abs(Math.sin(seconds * 6.1 + 0.73));
  const slow = Math.abs(Math.sin(seconds * 3.35 + 1.17));
  // Keep a readable but still bounded aperture for every frame of confirmed
  // playback.  The former 0.18 floor could be under 1 mm on this lip island,
  // which disappeared at ordinary conversation distance even though the
  // existing vertices were moving.  This remains an in-place deformation of
  // the authored lip island and is still hard-capped below at 10 mm.
  return Math.min(1, 0.32 + fast * 0.38 + medium * 0.20 + slow * 0.10);
}

/**
 * Deforms only the existing lip surface. `playing` must come from the audio
 * playback boundary, not a chat-submit or synthesis-start guess. The source
 * R6 body has no viseme morph targets or facial bones, so this fallback must
 * never be reported as a proven mouth opening or production lip sync.
 */
export function updateExistingMouthLipSyncRig(rig, {
  playing = false,
  seconds = 0,
  deltaSeconds = 0,
  smileAmount = 0,
} = {}) {
  if (!rig?.position || !rig?.region?.vertices) return false;
  rig.targetAmount = playing ? speechPulse(seconds) : 0;
  // Idle expression may gently shape the already-authored lip vertices. It is
  // intentionally disabled during speech so it cannot compete with lip sync.
  rig.targetSmileAmount = playing ? 0 : Math.max(0, Math.min(0.24, Number(smileAmount) || 0));
  const response = playing ? 21 : 28;
  const blend = 1 - Math.exp(-Math.max(0, deltaSeconds) * response);
  rig.amount += (rig.targetAmount - rig.amount) * blend;
  const smileBlend = 1 - Math.exp(-Math.max(0, deltaSeconds) * 6.5);
  rig.smileAmount += (rig.targetSmileAmount - rig.smileAmount) * smileBlend;
  if (!playing && rig.amount < 0.0005) rig.amount = 0;
  if (rig.targetSmileAmount === 0 && rig.smileAmount < 0.0005) rig.smileAmount = 0;
  const verticalAxis = Number.isInteger(rig.region.axes?.verticalAxis) ? rig.region.axes.verticalAxis : 2;
  const horizontalAxis = Number.isInteger(rig.region.axes?.horizontalAxis) ? rig.region.axes.horizontalAxis : 0;
  const depthAxis = Number.isInteger(rig.region.axes?.depthAxis) ? rig.region.axes.depthAxis : 1;
  const verticalExtent = Math.max(rig.region.fullBounds?.size?.[verticalAxis] || 0, EPSILON);
  const lipHeight = Math.max(rig.region.size?.[verticalAxis] || 0, EPSILON);
  // R6 is authored in metres.  The former envelope accidentally multiplied by
  // the *whole body* height and could pull the existing lower lip roughly
  // 29 mm away from the face.  Derive the aperture from the lip island itself
  // and hard-bound it to a human-scale 5.5--10.0 mm range.  `openDistance` is the
  // combined upper/lower aperture at the centre seam, not each lip's travel.
  const maximumOpeningDistance = Math.max(0.0055, Math.min(0.0100, lipHeight * 1.9));
  const openDistance = maximumOpeningDistance * rig.amount;
  const centerVertical = rig.region.center[verticalAxis];
  const centerHorizontal = rig.region.center[horizontalAxis];
  const halfHeight = Math.max(rig.region.size[verticalAxis] * 0.5, EPSILON);
  const halfWidth = Math.max(rig.region.size[horizontalAxis] * 0.5, EPSILON);
  let maximumAppliedDisplacement = 0;
  let maximumSeamDisplacement = 0;
  let maximumPerimeterDisplacement = 0;
  let maximumShade = 0;
  rig.region.vertices.forEach((vertex, offset) => {
    const base = [rig.base[offset * 3], rig.base[offset * 3 + 1], rig.base[offset * 3 + 2]];
    const normalized = Math.max(-1, Math.min(1, (base[verticalAxis] - centerVertical) / halfHeight));
    const horizontal = Math.max(-1, Math.min(1, (base[horizontalAxis] - centerHorizontal) / halfWidth));
    const upper = normalized >= 0;
    // The seam-facing vertices move most.  The outer vermilion border and the
    // mouth corners remain anchored to the surrounding face, preventing the
    // detached lower-lip/chin-patch silhouette seen in the v6 evidence.
    const outerT = Math.max(0, Math.min(1, (Math.abs(normalized) - 0.68) / 0.18));
    const outerSmooth = outerT * outerT * (3 - 2 * outerT);
    const verticalAnchor = 1 - outerSmooth;
    const seamWeight = Math.pow(Math.max(0, 1 - Math.abs(normalized)), 1.35) * verticalAnchor;
    const cornerStart = 0.58;
    const cornerT = Math.max(0, Math.min(1, (Math.abs(horizontal) - cornerStart) / (0.86 - cornerStart)));
    const cornerSmooth = cornerT * cornerT * (3 - 2 * cornerT);
    const horizontalAnchor = 1 - cornerSmooth;
    const deformationWeight = seamWeight * horizontalAnchor;
    const verticalOffset = openDistance * deformationWeight * (upper ? 0.50 : -0.50);
    // A sub-millimetre, seam-confined depth correction is enough to avoid face
    // occlusion without making the existing lip island float in front of the
    // head.  Outer vertices receive no depth offset.
    const maximumDepthOffset = Math.min(0.00035, lipHeight * 0.055);
    const depthOffset = maximumDepthOffset * rig.amount * deformationWeight;
    const cornerWeightRaw = Math.max(0, Math.min(1, (Math.abs(horizontal) - 0.42) / 0.58));
    const cornerWeight = cornerWeightRaw * cornerWeightRaw * (3 - 2 * cornerWeightRaw);
    const smileLift = verticalExtent * 0.0026 * rig.smileAmount * cornerWeight;
    const smileWiden = verticalExtent * 0.0007 * rig.smileAmount * cornerWeight * Math.sign(horizontal);
    for (let axis = 0; axis < 3; axis += 1) {
      const speech = axis === verticalAxis ? verticalOffset : axis === depthAxis ? depthOffset : 0;
      const smile = axis === verticalAxis ? smileLift : axis === horizontalAxis ? smileWiden : 0;
      setAttributeValue(rig.position, vertex, axis, base[axis] + speech + smile);
    }
    const appliedDisplacement = Math.hypot(
      verticalOffset + smileLift,
      depthOffset,
      smileWiden,
    );
    const speechDisplacement = Math.hypot(verticalOffset, depthOffset);
    maximumAppliedDisplacement = Math.max(maximumAppliedDisplacement, appliedDisplacement);
    if (Math.abs(normalized) <= 0.35 && Math.abs(horizontal) <= 0.58) {
      maximumSeamDisplacement = Math.max(maximumSeamDisplacement, speechDisplacement);
    }
    if (Math.abs(normalized) >= 0.86 || Math.abs(horizontal) >= 0.86) {
      maximumPerimeterDisplacement = Math.max(maximumPerimeterDisplacement, speechDisplacement);
    }
    if (rig.color && rig.baseColor) {
      // Warm only the true inner seam.  The steeper falloff keeps the darker
      // opening out of the outer lip and chin while making ordinary speech
      // readable at conversation distance.
      const shade = rig.amount * Math.pow(seamWeight, 3.0) * horizontalAnchor;
      maximumShade = Math.max(maximumShade, shade);
      const red = rig.baseColor[offset * 3] * (1 - shade * 0.55);
      const green = rig.baseColor[offset * 3 + 1] * (1 - shade * 0.72);
      const blue = rig.baseColor[offset * 3 + 2] * (1 - shade * 0.78);
      setAttributeValue(rig.color, vertex, 0, red);
      setAttributeValue(rig.color, vertex, 1, green);
      setAttributeValue(rig.color, vertex, 2, blue);
    }
  });
  rig.position.needsUpdate = true;
  if (rig.color) rig.color.needsUpdate = true;
  rig.restored = rig.amount === 0 && rig.smileAmount === 0;
  rig.updateCount += 1;
  rig.peakAmount = Math.max(rig.peakAmount, rig.amount);
  rig.peakSmileAmount = Math.max(rig.peakSmileAmount, rig.smileAmount);
  rig.openingDistance = openDistance;
  rig.maximumOpeningDistance = maximumOpeningDistance;
  rig.maximumAppliedDisplacement = maximumAppliedDisplacement;
  rig.maximumSeamDisplacement = maximumSeamDisplacement;
  rig.maximumPerimeterDisplacement = maximumPerimeterDisplacement;
  rig.innerLipShadeAmount = maximumShade;
  return true;
}

export function existingMouthLipSyncProbe(rig) {
  if (!rig) return { active: false, version: KIRA_EXISTING_MOUTH_LIPSYNC_VERSION };
  return {
    active: true,
    version: rig.version,
    meshName: rig.mesh?.name || null,
    vertexCount: rig.region?.vertices?.length || 0,
    regionScore: Number((rig.region?.score || 0).toFixed(6)),
    normalizedCenter: rig.region?.normalizedCenter?.map((value) => Number(value.toFixed(6))) || null,
    normalizedSize: rig.region?.normalizedSize?.map((value) => Number(value.toFixed(6))) || null,
    semanticAxes: rig.region?.axes || null,
    amount: Number((rig.amount || 0).toFixed(6)),
    peakAmount: Number((rig.peakAmount || 0).toFixed(6)),
    smileAmount: Number((rig.smileAmount || 0).toFixed(6)),
    peakSmileAmount: Number((rig.peakSmileAmount || 0).toFixed(6)),
    openingDistance: Number((rig.openingDistance || 0).toFixed(6)),
    maximumOpeningDistance: Number((rig.maximumOpeningDistance || 0).toFixed(6)),
    maximumAppliedDisplacement: Number((rig.maximumAppliedDisplacement || 0).toFixed(6)),
    maximumSeamDisplacement: Number((rig.maximumSeamDisplacement || 0).toFixed(6)),
    maximumPerimeterDisplacement: Number((rig.maximumPerimeterDisplacement || 0).toFixed(6)),
    innerLipShadeAmount: Number((rig.innerLipShadeAmount || 0).toFixed(6)),
    existingVertexColorSpeechShading: !!rig.existingVertexColorSpeechShading,
    updateCount: rig.updateCount || 0,
    restored: !!rig.restored,
    createdSceneNodes: 0,
    deformationOnly: true,
    sourceHasPhonemeMorphTargets: false,
    sourceHasFacialBones: false,
    visemeReady: false,
    visualMotionProven: false,
    method: "in_place_existing_position_attribute_bounded_seam_deformation_plus_anchored_perimeter_tint",
    drivenBy: "matched_actual_audio_playback_boundary_plus_suppressed_during_speech_ambient_smile",
    limitation: "speech-timed bounded existing-lip envelope and tiny idle corner lift only; the source body has no phoneme morph targets or facial bones",
  };
}
