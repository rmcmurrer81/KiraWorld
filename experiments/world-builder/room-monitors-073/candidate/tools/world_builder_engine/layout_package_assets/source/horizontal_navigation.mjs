// Isolated candidate: static, horizontal navigation acceptance.
// Foot points are [x, y, z] in meters. No browser, files, models, or resident state.
// Conservative square footprint; vertical connectors and moving doors are not modeled.
export const NAVIGATION_CONTRACT = "horizontal_support_candidate_v1";
const EPS = 1e-8;
const MAX_ITEMS = 128;
function fail(message) { throw new TypeError(message); }
function number(value, label) {
  if (!Number.isFinite(value) || Math.abs(value) > 1e6) fail(label + " must be a bounded finite number");
}
function vector(value, label) {
  if (!Array.isArray(value) || value.length !== 3) fail(label + " must be [x,y,z]");
  value.forEach((n) => number(n, label));
}
function validateScene(nav) {
  if (!nav || nav.contract !== NAVIGATION_CONTRACT) fail("Unsupported navigation contract");
  if (!Array.isArray(nav.support_surfaces) || nav.support_surfaces.length > MAX_ITEMS ||
      !Array.isArray(nav.colliders) || nav.colliders.length > MAX_ITEMS) fail("Invalid navigation geometry");
  const ids = new Set();
  for (const s of nav.support_surfaces) {
    if (!s || typeof s.id !== "string" || !s.id || ids.has(s.id)) fail("Invalid or duplicate support id");
    ids.add(s.id);
    for (const k of ["min_x", "max_x", "min_z", "max_z", "y"]) number(s[k], k);
    if (s.min_x >= s.max_x || s.min_z >= s.max_z) fail("Support must have positive area");
  }
  ids.clear();
  for (const c of nav.colliders) {
    if (!c || typeof c.id !== "string" || !c.id || ids.has(c.id)) fail("Invalid or duplicate collider id");
    ids.add(c.id); vector(c.min, "collider.min"); vector(c.max, "collider.max");
    if (c.min.some((n, i) => n >= c.max[i])) fail("Collider must have positive volume");
  }
}
function validateAvatar(radius, height) {
  number(radius, "avatar_radius"); number(height, "avatar_height");
  if (radius < 0.2 || radius > 0.6 || height < 0.5 || height > 3) fail("Invalid avatar dimensions");
}
function coplanar(nav, y) {
  // Exact shared elevation is deliberate: do not snap across levels or interpolate steps.
  return nav.support_surfaces.filter((s) => s.y === y);
}
function covered(point, radius, surfaces) {
  const x0 = point[0] - radius, x1 = point[0] + radius;
  const z0 = point[2] - radius, z1 = point[2] + radius;
  const xs = [x0, x1];
  for (const s of surfaces) {
    if (s.min_x > x0 && s.min_x < x1) xs.push(s.min_x);
    if (s.max_x > x0 && s.max_x < x1) xs.push(s.max_x);
  }
  xs.sort((a, b) => a - b);
  for (let i = 0; i < xs.length - 1; i += 1) {
    if (xs[i + 1] - xs[i] <= EPS) continue;
    const x = (xs[i] + xs[i + 1]) / 2;
    const intervals = surfaces.filter((s) => s.min_x <= x && x <= s.max_x &&
      s.max_z >= z0 && s.min_z <= z1).map((s) => [Math.max(z0, s.min_z), Math.min(z1, s.max_z)]);
    intervals.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    let reach = z0;
    for (const [start, end] of intervals) {
      if (start > reach + EPS) break;
      reach = Math.max(reach, end);
    }
    if (reach < z1 - EPS) return false;
  }
  return true;
}
function hitSegment(start, end, radius, height, c) {
  // Floor contact and touching a ceiling boundary are allowed; penetration is not.
  if (start[1] >= c.max[1] || start[1] + height <= c.min[1]) return false;
  let lo = 0, hi = 1;
  for (const axis of [0, 2]) {
    const origin = start[axis], delta = end[axis] - origin;
    const low = c.min[axis] - radius, high = c.max[axis] + radius;
    if (delta === 0) {
      if (origin < low || origin > high) return false;
    } else {
      let a = (low - origin) / delta, b = (high - origin) / delta;
      if (a > b) [a, b] = [b, a];
      lo = Math.max(lo, a); hi = Math.min(hi, b);
      if (lo > hi) return false;
    }
  }
  return true;
}
function supportSamples(start, end, radius, surfaces) {
  // The coverage topology changes only as a footprint edge crosses a support edge.
  // Check each event and each intervening interval, avoiding distance-based sampling.
  const events = [0, 1];
  for (const [axis, lowKey, highKey] of [[0, "min_x", "max_x"], [2, "min_z", "max_z"]]) {
    const delta = end[axis] - start[axis];
    if (delta === 0) continue;
    for (const s of surfaces) for (const edge of [s[lowKey], s[highKey]]) for (const offset of [-radius, radius]) {
      const t = (edge - offset - start[axis]) / delta;
      if (t > 0 && t < 1) events.push(t);
    }
  }
  const sorted = [...new Set(events)].sort((a, b) => a - b);
  const samples = [];
  sorted.forEach((t, i) => {
    if (i) samples.push((sorted[i - 1] + t) / 2);
    samples.push(t);
  });
  return samples;
}
function checkSegment(start, end, radius, height, nav) {
  if (start[1] !== end[1]) return { ok: false, reason: "vertical_transition_requires_connector" };
  const surfaces = coplanar(nav, start[1]);
  if (!surfaces.length) return { ok: false, reason: "unsupported_floor", t: 0, feet: [...start] };
  for (const t of supportSamples(start, end, radius, surfaces)) {
    const feet = [start[0] + (end[0] - start[0]) * t, start[1], start[2] + (end[2] - start[2]) * t];
    if (!covered(feet, radius, surfaces)) return { ok: false, reason: "unsupported_floor", t, feet };
  }
  for (const collider of nav.colliders) {
    if (hitSegment(start, end, radius, height, collider)) {
      return { ok: false, reason: "solid_obstruction", collider_id: collider.id };
    }
  }
  return { ok: true };
}
export function checkHorizontalRoute(route, nav) {
  validateScene(nav);
  if (!route || typeof route.id !== "string" || !route.id) fail("Route requires an id");
  validateAvatar(route.avatar_radius, route.avatar_height);
  if (!Array.isArray(route.points) || route.points.length < 2 || route.points.length > 320) fail("Route requires 2..320 foot points");
  route.points.forEach((p) => vector(p, "route point"));
  for (let i = 0; i < route.points.length - 1; i += 1) {
    const result = checkSegment(route.points[i], route.points[i + 1], route.avatar_radius, route.avatar_height, nav);
    if (!result.ok) return { route_id: route.id, status: "blocked", segment_index: i, ...result };
  }
  return { route_id: route.id, status: "clear", segment_count: route.points.length - 1, contract: NAVIGATION_CONTRACT };
}
export function checkWalkSpawn(feet, nav, radius = 0.34, height = 1.68) {
  validateScene(nav); vector(feet, "spawn feet"); validateAvatar(radius, height);
  return checkSegment(feet, feet, radius, height, nav);
}
