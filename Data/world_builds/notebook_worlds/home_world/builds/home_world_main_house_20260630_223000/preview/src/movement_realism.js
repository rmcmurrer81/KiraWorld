const TAU = Math.PI * 2;

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

export function wrapRadians(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.atan2(Math.sin(value), Math.cos(value));
}

export function shortestYawDelta(fromYaw, toYaw) {
  return wrapRadians(Number(toYaw || 0) - Number(fromYaw || 0));
}

/**
 * Acceleration-bounded shortest-arc yaw controller.
 *
 * The stopping-distance speed limit prevents an instant reversal at the target:
 * angular speed rises gradually, then falls early enough to stop without a snap.
 */
export function stepAcceleratedYaw(options = {}) {
  const yaw = wrapRadians(Number(options.yaw || 0));
  const targetYaw = wrapRadians(Number(options.targetYaw || 0));
  const dt = clamp(Number(options.dt || 0), 0, 0.1);
  const maxSpeed = Math.max(0.05, Number(options.maxSpeed || 2.65));
  const maxAcceleration = Math.max(0.05, Number(options.maxAcceleration || 6.4));
  const settleAngle = Math.max(0.0001, Number(options.settleAngle || 0.0025));
  const settleSpeed = Math.max(0.0001, Number(options.settleSpeed || 0.025));
  const currentVelocity = clamp(
    Number(options.angularVelocity || 0),
    -maxSpeed,
    maxSpeed,
  );
  const error = shortestYawDelta(yaw, targetYaw);

  if (dt <= 0) {
    return {
      yaw,
      angularVelocity: currentVelocity,
      angularAcceleration: 0,
      remainingRadians: Math.abs(error),
      aligned: Math.abs(error) <= settleAngle && Math.abs(currentVelocity) <= settleSpeed,
      overshot: false,
    };
  }

  if (Math.abs(error) <= settleAngle && Math.abs(currentVelocity) <= settleSpeed) {
    return {
      yaw: targetYaw,
      angularVelocity: 0,
      angularAcceleration: -currentVelocity / dt,
      remainingRadians: 0,
      aligned: true,
      overshot: false,
    };
  }

  const direction = Math.sign(error || currentVelocity || 1);
  const stoppingLimitedSpeed = Math.sqrt(Math.max(0, 2 * maxAcceleration * Math.abs(error)));
  const desiredVelocity = direction * Math.min(maxSpeed, stoppingLimitedSpeed);
  const velocityDelta = clamp(
    desiredVelocity - currentVelocity,
    -maxAcceleration * dt,
    maxAcceleration * dt,
  );
  let nextVelocity = clamp(currentVelocity + velocityDelta, -maxSpeed, maxSpeed);
  let yawStep = nextVelocity * dt;
  let nextYaw = wrapRadians(yaw + yawStep);
  let overshot = false;

  if (Math.sign(yawStep) === Math.sign(error) && Math.abs(yawStep) >= Math.abs(error)) {
    nextYaw = targetYaw;
    nextVelocity = 0;
    yawStep = error;
    overshot = true;
  }

  const remaining = Math.abs(shortestYawDelta(nextYaw, targetYaw));
  return {
    yaw: nextYaw,
    angularVelocity: nextVelocity,
    angularAcceleration: velocityDelta / dt,
    remainingRadians: remaining,
    aligned: remaining <= settleAngle && Math.abs(nextVelocity) <= settleSpeed,
    overshot,
  };
}

/** Translation stops during a large turn and eases in only as alignment improves. */
export function translationScaleForTurn(
  remainingRadians,
  stopRadians = 1.05,
  fullSpeedRadians = 0.16,
) {
  const remaining = Math.max(0, Number(remainingRadians || 0));
  const stop = Math.max(0.01, Number(stopRadians || 1.05));
  const full = clamp(Number(fullSpeedRadians || 0.16), 0, stop - 0.001);
  if (remaining >= stop) return 0;
  if (remaining <= full) return 1;
  const k = clamp((stop - remaining) / (stop - full), 0, 1);
  return k * k * (3 - 2 * k);
}

/** Frame-rate-independent start/stop blend used by limbs, pelvis, and root motion. */
export function advanceLocomotionBlend(current, desired, dt, options = {}) {
  const from = clamp(Number(current || 0), 0, 1);
  const to = clamp(Number(desired || 0), 0, 1);
  const seconds = to > from
    ? Math.max(0.04, Number(options.riseSeconds || 0.24))
    : Math.max(0.04, Number(options.fallSeconds || 0.34));
  const safeDt = clamp(Number(dt || 0), 0, 0.1);
  if (safeDt <= 0) return from;
  const alpha = 1 - Math.exp(-safeDt / seconds);
  const next = from + (to - from) * alpha;
  if (Math.abs(next - to) < 0.001) return to;
  return clamp(next, 0, 1);
}

export const DEFAULT_AVOIDANCE_OFFSETS_RADIANS = Object.freeze([
  0,
  Math.PI / 18,
  -Math.PI / 18,
  Math.PI / 9,
  -Math.PI / 9,
  Math.PI * 0.19,
  -Math.PI * 0.19,
  Math.PI * 0.29,
  -Math.PI * 0.29,
]);

/**
 * Selects a combined X/Z step only when both that step and its look-ahead are
 * collision free. It never decomposes motion into wall-sliding axis writes.
 */
export function selectCollisionFreeHeading(options = {}) {
  const originX = Number(options.originX || 0);
  const originZ = Number(options.originZ || 0);
  const desiredHeading = Number(options.desiredHeading || 0);
  const stepDistance = Math.max(0, Number(options.stepDistance || 0));
  const lookAheadDistance = Math.max(stepDistance, Number(options.lookAheadDistance || stepDistance));
  const sampleSpacing = clamp(Number(options.sampleSpacing || 0.12), 0.04, 0.25);
  const blocked = typeof options.isBlocked === "function" ? options.isBlocked : () => false;
  const offsets = Array.isArray(options.offsets) && options.offsets.length
    ? options.offsets
    : DEFAULT_AVOIDANCE_OFFSETS_RADIANS;

  for (const offset of offsets) {
    const heading = wrapRadians(desiredHeading + Number(offset || 0));
    const directionX = Math.sin(heading);
    const directionZ = Math.cos(heading);
    const nextX = originX + directionX * stepDistance;
    const nextZ = originZ + directionZ * stepDistance;
    const lookAheadX = originX + directionX * lookAheadDistance;
    const lookAheadZ = originZ + directionZ * lookAheadDistance;
    let pathBlocked = false;
    const samples = Math.max(1, Math.ceil(lookAheadDistance / sampleSpacing));
    for (let index = 1; index <= samples; index += 1) {
      const distance = Math.min(lookAheadDistance, index * lookAheadDistance / samples);
      if (blocked(originX + directionX * distance, originZ + directionZ * distance)) {
        pathBlocked = true;
        break;
      }
    }
    if (pathBlocked) continue;
    return {
      heading,
      offsetRadians: Number(offset || 0),
      nextX,
      nextZ,
      lookAheadX,
      lookAheadZ,
      direct: Math.abs(Number(offset || 0)) < 1e-6,
    };
  }
  return null;
}

function finitePoint2D(point) {
  if (!point) return null;
  const x = Number(point.x);
  const z = Number(point.z);
  return Number.isFinite(x) && Number.isFinite(z) ? { x, z } : null;
}

function pointSegmentIsClear(from, to, isBlocked, sampleSpacing = 0.1) {
  const distance = Math.hypot(to.x - from.x, to.z - from.z);
  const samples = Math.max(1, Math.ceil(distance / Math.max(0.04, sampleSpacing)));
  for (let index = 1; index <= samples; index += 1) {
    const k = index / samples;
    if (isBlocked(
      from.x + (to.x - from.x) * k,
      from.z + (to.z - from.z) * k,
    )) return false;
  }
  return true;
}

/**
 * Deterministic bounded A* route for a body already inside a room/building.
 *
 * Returned waypoints exclude `start`: callers must walk the body from its
 * current transform.  The planner never writes a transform and therefore
 * cannot teleport or conceal an unreachable interaction target.
 */
export function planCollisionFreeGridRoute(options = {}) {
  const start = finitePoint2D(options.start);
  const goal = finitePoint2D(options.goal);
  const bounds = options.bounds || {};
  const minX = Number(bounds.minX);
  const maxX = Number(bounds.maxX);
  const minZ = Number(bounds.minZ);
  const maxZ = Number(bounds.maxZ);
  const cellSize = clamp(Number(options.cellSize || 0.3), 0.12, 1.0);
  const sampleSpacing = clamp(Number(options.sampleSpacing || 0.09), 0.04, 0.25);
  const maxVisited = Math.max(64, Math.floor(Number(options.maxVisited || 7000)));
  const isBlocked = typeof options.isBlocked === "function" ? options.isBlocked : () => false;
  const validBounds = [minX, maxX, minZ, maxZ].every(Number.isFinite)
    && minX < maxX && minZ < maxZ;
  if (!start || !goal || !validBounds) {
    return { ok: false, waypoints: [], reason: "invalid_route_request", visitedNodes: 0 };
  }
  const insideBounds = (point) => point.x >= minX && point.x <= maxX && point.z >= minZ && point.z <= maxZ;
  if (!insideBounds(start) || !insideBounds(goal)) {
    return { ok: false, waypoints: [], reason: "endpoint_outside_route_bounds", visitedNodes: 0 };
  }
  if (isBlocked(start.x, start.z)) {
    return { ok: false, waypoints: [], reason: "start_position_blocked", visitedNodes: 0 };
  }
  if (isBlocked(goal.x, goal.z)) {
    return { ok: false, waypoints: [], reason: "interaction_goal_blocked", visitedNodes: 0 };
  }
  if (pointSegmentIsClear(start, goal, isBlocked, sampleSpacing)) {
    return {
      ok: true,
      waypoints: [{ ...goal }],
      reason: "direct_segment_clear",
      mode: "direct_collision_checked",
      visitedNodes: 0,
    };
  }

  const countX = Math.max(2, Math.floor((maxX - minX) / cellSize) + 1);
  const countZ = Math.max(2, Math.floor((maxZ - minZ) / cellSize) + 1);
  const gridPoint = (ix, iz) => ({
    x: minX + Math.min(ix, countX - 1) * cellSize,
    z: minZ + Math.min(iz, countZ - 1) * cellSize,
  });
  const keyFor = (ix, iz) => `${ix},${iz}`;
  const inGrid = (ix, iz) => ix >= 0 && ix < countX && iz >= 0 && iz < countZ;
  const passableCache = new Map();
  const passable = (ix, iz) => {
    if (!inGrid(ix, iz)) return false;
    const key = keyFor(ix, iz);
    if (!passableCache.has(key)) {
      const point = gridPoint(ix, iz);
      passableCache.set(key, insideBounds(point) && !isBlocked(point.x, point.z));
    }
    return passableCache.get(key);
  };
  const nearestGridCell = (point, requireConnectionFromPoint) => {
    const baseX = clamp(Math.round((point.x - minX) / cellSize), 0, countX - 1);
    const baseZ = clamp(Math.round((point.z - minZ) / cellSize), 0, countZ - 1);
    const candidates = [];
    const maxRing = Math.min(10, Math.max(countX, countZ));
    for (let ring = 0; ring <= maxRing; ring += 1) {
      candidates.length = 0;
      for (let dx = -ring; dx <= ring; dx += 1) {
        for (let dz = -ring; dz <= ring; dz += 1) {
          if (Math.max(Math.abs(dx), Math.abs(dz)) !== ring) continue;
          const ix = baseX + dx;
          const iz = baseZ + dz;
          if (!passable(ix, iz)) continue;
          const grid = gridPoint(ix, iz);
          if (!requireConnectionFromPoint(point, grid)) continue;
          candidates.push({ ix, iz, grid, distance: Math.hypot(grid.x - point.x, grid.z - point.z) });
        }
      }
      if (candidates.length) {
        candidates.sort((a, b) => a.distance - b.distance || a.iz - b.iz || a.ix - b.ix);
        return candidates[0];
      }
    }
    return null;
  };
  const startCell = nearestGridCell(
    start,
    (exact, grid) => pointSegmentIsClear(exact, grid, isBlocked, sampleSpacing),
  );
  const goalCell = nearestGridCell(
    goal,
    (exact, grid) => pointSegmentIsClear(grid, exact, isBlocked, sampleSpacing),
  );
  if (!startCell || !goalCell) {
    return {
      ok: false,
      waypoints: [],
      reason: !startCell ? "no_clear_grid_connection_from_start" : "no_clear_grid_connection_to_goal",
      visitedNodes: 0,
    };
  }

  const directions = [
    [0, -1, 1], [1, 0, 1], [0, 1, 1], [-1, 0, 1],
    [1, -1, Math.SQRT2], [1, 1, Math.SQRT2], [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2],
  ];
  const startKey = keyFor(startCell.ix, startCell.iz);
  const goalKey = keyFor(goalCell.ix, goalCell.iz);
  const records = new Map([[startKey, {
    ix: startCell.ix,
    iz: startCell.iz,
    g: 0,
    f: Math.hypot(goalCell.ix - startCell.ix, goalCell.iz - startCell.iz),
    parent: null,
  }]]);
  const open = [startKey];
  const closed = new Set();
  let visitedNodes = 0;

  while (open.length && visitedNodes < maxVisited) {
    open.sort((aKey, bKey) => {
      const a = records.get(aKey);
      const b = records.get(bKey);
      return a.f - b.f || a.g - b.g || a.iz - b.iz || a.ix - b.ix;
    });
    const currentKey = open.shift();
    if (closed.has(currentKey)) continue;
    const current = records.get(currentKey);
    closed.add(currentKey);
    visitedNodes += 1;
    if (currentKey === goalKey) break;

    for (const [dx, dz, moveCost] of directions) {
      const ix = current.ix + dx;
      const iz = current.iz + dz;
      if (!passable(ix, iz)) continue;
      if (dx !== 0 && dz !== 0 && (!passable(current.ix + dx, current.iz) || !passable(current.ix, current.iz + dz))) continue;
      const from = gridPoint(current.ix, current.iz);
      const to = gridPoint(ix, iz);
      if (!pointSegmentIsClear(from, to, isBlocked, sampleSpacing)) continue;
      const neighborKey = keyFor(ix, iz);
      if (closed.has(neighborKey)) continue;
      const tentativeG = current.g + moveCost;
      const previous = records.get(neighborKey);
      if (previous && tentativeG >= previous.g - 1e-9) continue;
      const heuristic = Math.hypot(goalCell.ix - ix, goalCell.iz - iz);
      records.set(neighborKey, {
        ix,
        iz,
        g: tentativeG,
        f: tentativeG + heuristic,
        parent: currentKey,
      });
      if (!open.includes(neighborKey)) open.push(neighborKey);
    }
  }

  if (!closed.has(goalKey)) {
    return {
      ok: false,
      waypoints: [],
      reason: visitedNodes >= maxVisited ? "route_search_budget_exhausted" : "no_collision_free_route",
      visitedNodes,
    };
  }

  const gridPath = [];
  let cursor = goalKey;
  while (cursor) {
    const record = records.get(cursor);
    if (!record) break;
    gridPath.push(gridPoint(record.ix, record.iz));
    cursor = record.parent;
  }
  gridPath.reverse();
  const raw = [start, ...gridPath, goal].filter((point, index, list) => (
    index === 0 || Math.hypot(point.x - list[index - 1].x, point.z - list[index - 1].z) > 0.01
  ));
  const simplified = [raw[0]];
  let anchor = 0;
  while (anchor < raw.length - 1) {
    let next = raw.length - 1;
    while (next > anchor + 1 && !pointSegmentIsClear(raw[anchor], raw[next], isBlocked, sampleSpacing)) next -= 1;
    simplified.push(raw[next]);
    anchor = next;
  }
  return {
    ok: true,
    waypoints: simplified.slice(1).map((point) => ({ x: point.x, z: point.z })),
    reason: "bounded_grid_route_found",
    mode: "bounded_collision_checked_astar",
    visitedNodes,
    rawWaypointCount: raw.length - 1,
  };
}

/** Detects pacing/oscillation without confusing ordinary turns with failure. */
export function updateRouteProgressWatch(previous = null, sample = {}, options = {}) {
  const t = Number(sample.t);
  const x = Number(sample.x);
  const z = Number(sample.z);
  const distance = Math.max(0, Number(sample.distance));
  if (![t, x, z, distance].every(Number.isFinite)) {
    return { ...(previous || {}), status: "invalid_sample", stalled: false, oscillating: false };
  }
  const improvementMeters = Math.max(0.01, Number(options.improvementMeters || 0.06));
  const windowSeconds = Math.max(0.8, Number(options.windowSeconds || 2.2));
  const stallSeconds = Math.max(windowSeconds, Number(options.stallSeconds || 2.8));
  const minimumTravelMeters = Math.max(0.2, Number(options.minimumTravelMeters || 0.75));
  const maximumNetMeters = Math.max(0.04, Number(options.maximumNetMeters || 0.24));
  const goalToleranceMeters = Math.max(0.1, Number(options.goalToleranceMeters || 0.38));
  const priorBest = Number.isFinite(previous?.bestDistance) ? previous.bestDistance : distance;
  const progressReferenceDistance = Number.isFinite(previous?.progressReferenceDistance)
    ? previous.progressReferenceDistance
    : distance;
  const meaningfullyImproved = distance <= progressReferenceDistance - improvementMeters;
  const bestDistance = Math.min(priorBest, distance);
  const nextProgressReferenceDistance = meaningfullyImproved ? distance : progressReferenceDistance;
  const lastProgressAt = meaningfullyImproved
    ? t
    : Number.isFinite(previous?.lastProgressAt) ? previous.lastProgressAt : t;
  const samples = [...(Array.isArray(previous?.samples) ? previous.samples : []), { t, x, z, distance }]
    .filter((entry) => t - entry.t <= windowSeconds + 0.12);
  let pathLengthMeters = 0;
  for (let index = 1; index < samples.length; index += 1) {
    pathLengthMeters += Math.hypot(samples[index].x - samples[index - 1].x, samples[index].z - samples[index - 1].z);
  }
  const first = samples[0];
  const windowDurationSeconds = first ? Math.max(0, t - first.t) : 0;
  const netMeters = first ? Math.hypot(x - first.x, z - first.z) : 0;
  const awayFromGoal = distance > goalToleranceMeters;
  const oscillating = awayFromGoal
    && windowDurationSeconds >= windowSeconds * 0.9
    && pathLengthMeters >= minimumTravelMeters
    && netMeters <= maximumNetMeters;
  const stalled = awayFromGoal && t - lastProgressAt >= stallSeconds;
  return {
    bestDistance,
    progressReferenceDistance: nextProgressReferenceDistance,
    lastProgressAt,
    samples,
    pathLengthMeters,
    netMeters,
    windowDurationSeconds,
    stalled,
    oscillating,
    status: oscillating ? "oscillating" : stalled ? "stalled" : "progressing",
  };
}

/**
 * Builds a narrow, centered route through a wall opening.
 *
 * Door navigation must not jump from an outside porch point to an arbitrary
 * indoor room point: that diagonal can cross the wall beside the opening.
 * These three ordered points keep the whole crossing on the opening's
 * centerline. `outsideSign` is +1 when the outside is at increasing Z.
 */
export function buildCenteredDoorwayCorridor(options = {}) {
  const entryX = Number(options.entryX || 0);
  const wallZ = Number(options.wallZ || 0);
  const y = Number(options.y || 0);
  const outsideSign = Number(options.outsideSign) < 0 ? -1 : 1;
  const outsideDistance = Math.max(0.55, Number(options.outsideDistance || 1.05));
  const insideDistance = Math.max(0.55, Number(options.insideDistance || 1.05));
  return [
    {
      id: "doorway_outside_threshold",
      x: entryX,
      y,
      z: wallZ + outsideSign * outsideDistance,
    },
    {
      id: "doorway_centerline",
      x: entryX,
      y,
      z: wallZ,
    },
    {
      id: "doorway_inside_threshold",
      x: entryX,
      y,
      z: wallZ - outsideSign * insideDistance,
    },
  ];
}

export function withinJointLimit(value, minimum, maximum, tolerance = 1e-8) {
  const number = Number(value);
  return Number.isFinite(number)
    && number >= Number(minimum) - tolerance
    && number <= Number(maximum) + tolerance;
}

export { TAU };
