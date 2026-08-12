import test from "node:test";
import assert from "node:assert/strict";

import {
  planCollisionFreeGridRoute,
  selectCollisionFreeHeading,
  updateRouteProgressWatch,
} from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/movement_realism.js";

const exactIncidentStart = { x: -18.301, z: 2.634 };
const incidentStart = { x: -19.334, z: 2.652 };
const coffeeTarget = { x: -17.95, z: -0.22 };
const drinkTarget = { x: -21.602, z: -1.0 };
const interiorBounds = { minX: -31.45, maxX: -14.55, minZ: -2.75, maxZ: 8.95 };

// Runtime TV/media-console collider expanded by Kira's 0.46 m body radius.
const inflatedTv = { minX: -20.941, maxX: -18.261, minZ: 1.17, maxZ: 2.63 };
const isTvBlocked = (x, z) => (
  x >= inflatedTv.minX && x <= inflatedTv.maxX
  && z >= inflatedTv.minZ && z <= inflatedTv.maxZ
);

function segmentIsClear(from, to, blocked = isTvBlocked) {
  const distance = Math.hypot(to.x - from.x, to.z - from.z);
  const samples = Math.max(1, Math.ceil(distance / 0.04));
  for (let index = 1; index <= samples; index += 1) {
    const k = index / samples;
    if (blocked(
      from.x + (to.x - from.x) * k,
      from.z + (to.z - from.z) * k,
    )) return false;
  }
  return true;
}

for (const [label, target] of [["coffee", coffeeTarget], ["generic drink", drinkTarget]]) {
  test(`06:51 incident ${label} route detours around the inflated TV collider`, () => {
    assert.equal(segmentIsClear(incidentStart, target), false, "the old direct route must reproduce the TV collision");
    const plan = planCollisionFreeGridRoute({
      start: incidentStart,
      goal: target,
      bounds: interiorBounds,
      cellSize: 0.28,
      sampleSpacing: 0.04,
      isBlocked: isTvBlocked,
    });
    assert.equal(plan.ok, true, plan.reason);
    assert.equal(plan.mode, "bounded_collision_checked_astar");
    assert.ok(plan.waypoints.length >= 2, "blocked direct routes need a visible detour waypoint");
    let previous = incidentStart;
    for (const waypoint of plan.waypoints) {
      assert.equal(isTvBlocked(waypoint.x, waypoint.z), false);
      assert.equal(segmentIsClear(previous, waypoint), true, `unsafe segment ${JSON.stringify(previous)} -> ${JSON.stringify(waypoint)}`);
      previous = waypoint;
    }
    assert.ok(Math.hypot(previous.x - target.x, previous.z - target.z) < 0.001);
  });
}

test("planner and local steering agree at the exact millimetre-close TV incident start", () => {
  assert.equal(segmentIsClear(exactIncidentStart, coffeeTarget), false);
  const plan = planCollisionFreeGridRoute({
    start: exactIncidentStart,
    goal: coffeeTarget,
    bounds: interiorBounds,
    cellSize: 0.28,
    sampleSpacing: 0.04,
    isBlocked: isTvBlocked,
  });
  assert.equal(plan.ok, true, plan.reason);
  assert.ok(plan.waypoints.length >= 2);
  const first = plan.waypoints[0];
  const distance = Math.hypot(first.x - exactIncidentStart.x, first.z - exactIncidentStart.z);
  const desiredHeading = Math.atan2(
    first.x - exactIncidentStart.x,
    first.z - exactIncidentStart.z,
  );
  const steering = selectCollisionFreeHeading({
    originX: exactIncidentStart.x,
    originZ: exactIncidentStart.z,
    desiredHeading,
    stepDistance: Math.min(distance, 0.82 / 60),
    lookAheadDistance: Math.min(distance, 0.34),
    isBlocked: isTvBlocked,
  });
  assert.ok(steering, "a route waypoint must not be rejected by the frame-level steering sweep");
  assert.equal(steering.direct, true, "the first planned segment itself should be collision free");
});

test("bounded planner fails truthfully when an interior wall leaves no route", () => {
  const wall = (x, z) => z >= 0.75 && z <= 1.25;
  const plan = planCollisionFreeGridRoute({
    start: { x: 0, z: 2.5 },
    goal: { x: 0, z: -2.5 },
    bounds: { minX: -2, maxX: 2, minZ: -3, maxZ: 3 },
    cellSize: 0.25,
    isBlocked: wall,
  });
  assert.equal(plan.ok, false);
  assert.equal(plan.reason, "no_collision_free_route");
  assert.deepEqual(plan.waypoints, []);
});

test("progress watch distinguishes useful travel from back-and-forth pacing", () => {
  let watch = null;
  for (let index = 0; index <= 30; index += 1) {
    const x = index % 2 === 0 ? 0 : 0.12;
    watch = updateRouteProgressWatch(watch, {
      t: index * 0.1,
      x,
      z: 0,
      distance: 2.79,
    }, {
      windowSeconds: 2.2,
      stallSeconds: 2.8,
      minimumTravelMeters: 0.75,
      maximumNetMeters: 0.24,
    });
  }
  assert.equal(watch.oscillating, true);
  assert.equal(watch.status, "oscillating");

  watch = null;
  for (let index = 0; index <= 30; index += 1) {
    watch = updateRouteProgressWatch(watch, {
      t: index * 0.1,
      x: index * 0.04,
      z: 0,
      distance: 2.79 - index * 0.04,
    });
  }
  assert.equal(watch.oscillating, false);
  assert.equal(watch.stalled, false);
  assert.equal(watch.status, "progressing");
});
