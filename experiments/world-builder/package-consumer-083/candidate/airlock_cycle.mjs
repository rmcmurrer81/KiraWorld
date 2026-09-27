// Authored fiction only: no pressure units, sensors, pump model, seal or latch physics.
export const CONTRACT = 'fictional_airlock_cycle_v1';
export const LABEL = 'Fictional airlock simulation — not live telemetry or pressure engineering';
const bindings = new WeakSet();
const check = (ok, message) => { if (!ok) throw new TypeError(message); };
const freeze = value => { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const id = value => typeof value === 'string' && value.length > 0 && value.length < 180;

// The host MUST first admit the bytes and bind the actual GLB using its existing
// loader. This is a sidecar association check, not a replacement package verifier.
// Side roles are nominated explicitly; neither room names nor ordering infer Mars.
export function bindAirlockCycle(metadata, options) {
  const {manifestSha256, sceneSha256, pairId, insideDoorId, outsideDoorId, roleAssignment} = options ?? {};
  check(metadata?.contract === 'world_scene_metadata_v2' && id(metadata.scene_id), 'Unsupported scene');
  check(hash(manifestSha256) && hash(sceneSha256), 'Exact package and scene hashes required');
  check(roleAssignment === 'explicit_fictional_habitat_mars', 'Explicit fictional side assignment required');
  check(id(insideDoorId) && id(outsideDoorId) && insideDoorId !== outsideDoorId, 'Distinct nominated doors required');
  check(Array.isArray(metadata.airlock_pairs) && Array.isArray(metadata.doors) && Array.isArray(metadata.rooms), 'Missing metadata');
  const pairs = metadata.airlock_pairs.filter(p => p.id === pairId);
  check(pairs.length === 1, 'Exact unique pair required');
  const pair = pairs[0], room = metadata.rooms.filter(r => r.id === pair.room_id);
  check(room.length === 1 && room[0].functional_role === 'airlock', 'Exact airlock room required');
  check(pair.contract === 'paired_airlock_door_sequence_v1' && pair.pressure_simulation === false && pair.state_persistence === 'session_local', 'Unsupported underlying pair');
  check(Array.isArray(pair.door_ids) && pair.door_ids.length === 2 && new Set(pair.door_ids).size === 2 && pair.door_ids.includes(insideDoorId) && pair.door_ids.includes(outsideDoorId), 'Nominated doors differ from pair');
  check(pair.opening_policy?.requires_peer === 'closed_and_stopped' && same(pair.opening_policy.blocked_peer_conditions, ['nonzero_angle', 'moving', 'nonzero_target', 'motion_held']) && pair.closing_policy === 'existing_reach_motion_and_occupancy_rules', 'Underlying interlock must remain intact');
  const ports = Object.fromEntries([['inside', insideDoorId], ['outside', outsideDoorId]].map(([side, doorId]) => {
    const matches = metadata.doors.filter(d => d.id === doorId); check(matches.length === 1, 'Exact unique door required');
    const d = matches[0], index = pair.door_ids.indexOf(doorId);
    check(d.leaf_node_id === pair.leaf_node_ids?.[index] && d.portal_id === pair.portal_ids?.[index], 'Door leaf or portal differs');
    check(d.pressure_simulation === false && d.state_persistence === 'session_local' && d.initial_state === 'closed', 'Underlying door behavior differs');
    check(Array.isArray(d.room_ids) && d.room_ids.length === 2 && new Set(d.room_ids).size === 2 && d.room_ids.includes(pair.room_id), 'Door adjacency differs');
    check(d.interlock_pair_ids?.includes(pairId) && d.interaction?.rules?.includes('paired_airlock_peer_closed_stopped'), 'Underlying door interlock missing');
    check(d.hinge?.closed_angle === 0 && Number.isFinite(d.hinge.open_angle) && Math.abs(Math.abs(d.hinge.open_angle) - Math.PI / 2) < 1e-7, 'Unsupported door angle');
    const adjacentRoomId = d.room_ids.find(r => r !== pair.room_id);
    check(metadata.rooms.filter(r => r.id === adjacentRoomId).length === 1, 'Missing adjacent room');
    return [side, {doorId, leafNodeId: d.leaf_node_id, portalId: d.portal_id, adjacentRoomId, openAngle: d.hinge.open_angle, simulatedSide: side === 'inside' ? 'habitat' : 'mars'}];
  }));
  const result = freeze({contract: CONTRACT, manifestSha256, sceneSha256, sceneId: metadata.scene_id, pairId, roomId: pair.room_id, roleAssignment, ports});
  bindings.add(result); return result;
}

// Synchronous ports retain the host's reach, occupied-swing, collision and motion
// checks. readDoors returns these exact hashes and exactly the nominated two poses.
// toggleDoor must use the SAME captured runtime, never a mutable current-world ref.
export function createAirlockCycle({binding, runtimeIdentity, readDoors, toggleDoor, cycleSeconds = 6}) {
  check(bindings.has(binding), 'Use the exact binding returned by bindAirlockCycle');
  check(runtimeIdentity !== null && typeof runtimeIdentity === 'object', 'A captured runtime instance identity is required');
  check(typeof readDoors === 'function' && typeof toggleDoor === 'function', 'Synchronous door ports required');
  check(Number.isFinite(cycleSeconds) && cycleSeconds >= 2 && cycleSeconds <= 30, 'Authored cycle duration must be 2–30 seconds');
  const sides = ['inside', 'outside'], seals = {inside: false, outside: false};
  let phase = 'idle', pressure = 'unknown', target = null, elapsed = 0, token = null, disposed = false, locked = false;
  let poses = null, reason = null;
  const closed = p => p.angle === 0 && p.target === 0 && !p.moving && !p.motionHeld;
  const fail = why => ({ok: false, reason: why});
  function invalidate(why) { phase = 'fault'; pressure = 'unknown'; target = null; elapsed = 0; token = null; seals.inside = seals.outside = false; reason = why; }
  function read() {
    try {
      const r = readDoors();
      check(r && !r.then && r.runtimeIdentity === runtimeIdentity && r.manifestSha256 === binding.manifestSha256 && r.sceneSha256 === binding.sceneSha256 && r.sceneId === binding.sceneId, 'Door runtime/package binding changed');
      check(Array.isArray(r.doors) && r.doors.length === 2 && new Set(r.doors.map(d => d.id)).size === 2, 'Exact two door observations required');
      const next = {};
      for (const side of sides) {
        const port = binding.ports[side], rows = r.doors.filter(d => d.id === port.doorId); check(rows.length === 1, 'Door identity changed');
        const d = rows[0];
        check(Number.isFinite(d.angle) && d.angle * port.openAngle >= 0 && Math.abs(d.angle) <= Math.abs(port.openAngle) && [0, port.openAngle].includes(d.target) && typeof d.moving === 'boolean' && typeof d.motionHeld === 'boolean', 'Invalid authoritative door pose');
        next[side] = {id: d.id, angle: d.angle, target: d.target, moving: d.moving, motionHeld: d.motionHeld};
      }
      poses = next;
      for (const side of sides) if (!closed(poses[side])) seals[side] = false;
      if (['cycling', 'paused'].includes(phase) && sides.some(side => !closed(poses[side]) || !seals[side])) invalidate('Door or simulated seal changed during cycle');
      // A foreign bypass cannot restore pressure by merely closing the door later.
      if (sides.some(side => !closed(poses[side]) && pressure !== binding.ports[side].simulatedSide)) invalidate('Door moved with incompatible or unknown simulated pressure');
      return true;
    } catch (error) { invalidate(error.message); return false; }
  }
  function exclusive(action) {
    check(!locked, 'Reentrant airlock operation');
    if (disposed) return fail('disposed');
    locked = true;
    try { return read() ? action() : fail(reason); } finally { locked = false; }
  }
  const busy = () => phase === 'cycling' || phase === 'paused';
  const bothSealed = () => sides.every(side => closed(poses[side]) && seals[side]);
  const validSide = side => check(sides.includes(side), 'Unknown airlock port');
  function snapshotValue() {
    return freeze({contract: CONTRACT, label: LABEL, binding, phase, simulatedPressure: pressure, target, elapsedSeconds: elapsed,
      authoredCycleSeconds: cycleSeconds, simulatedSealAcknowledged: {...seals}, doors: poses ? structuredClone(poses) : null, reason,
      capabilities: {fictionalStateOnly: true, liveTelemetry: false, pressurePhysics: false, mechanicalSeal: false, latchAnimation: false, nasaDesign: false}});
  }
  function move(side, opening) { return exclusive(() => {
    validSide(side); const peer = side === 'inside' ? 'outside' : 'inside', pose = poses[side];
    if (busy()) return fail('Cancel the simulated cycle before any door command');
    if (pose.moving || pose.motionHeld) return fail('Door is moving or motion-held');
    if (opening) {
      if (!closed(pose)) return fail('Door is not closed and stopped');
      if (pressure !== binding.ports[side].simulatedSide) return fail('Incompatible or unknown simulated pressure');
      if (!closed(poses[peer]) || !seals[peer]) return fail('Peer must be closed, stopped and simulation-seal acknowledged');
    } else if (closed(pose)) return {ok: true, unchanged: true};
    let result;
    try { result = toggleDoor(binding.ports[side].doorId); }
    catch (error) { invalidate('Door command outcome unknown: ' + error.message); return fail(reason); }
    if (!result || result.then || typeof result.ok !== 'boolean') { invalidate('Door command must return a synchronous known outcome'); return fail(reason); }
    const readOK = read();
    if (!readOK || (opening && phase === 'fault')) return fail(reason);
    if (!result.ok) return fail(result.reason || 'Existing door runtime rejected command');
    const expected = opening ? binding.ports[side].openAngle : 0;
    if (poses[side].target !== expected || (!poses[side].moving && poses[side].angle !== expected)) { invalidate('Door command was not synchronously observed'); return fail(reason); }
    seals[side] = false;
    return {ok: true, doorId: binding.ports[side].doorId, action: opening ? 'opening' : 'closing'};
  }); }
  return Object.freeze({
    snapshot() { if (!disposed) exclusive(() => ({ok: true})); return snapshotValue(); },
    acknowledgeSimulatedSeal(side, value = true) { return exclusive(() => {
      validSide(side); check(typeof value === 'boolean', 'Seal acknowledgement must be boolean');
      if (busy()) return fail('Cycle must be cancelled before changing seal acknowledgement');
      if (!closed(poses[side])) return fail('A geometric closed/stopped state is required first');
      seals[side] = value; return {ok: true};
    }); },
    open: side => move(side, true), close: side => move(side, false),
    begin(destination) { return exclusive(() => {
      check(['habitat', 'mars'].includes(destination), 'Unknown fictional destination');
      if (busy()) return fail('A cycle is already active');
      if (!bothSealed()) return fail('Both doors must be closed/stopped and simulation-seal acknowledged');
      phase = 'cycling'; pressure = 'unknown'; target = destination; elapsed = 0; reason = null; token = Object.freeze({});
      return {ok: true, token};
    }); },
    advance(runToken, seconds) {
      if (disposed || runToken !== token || !token || phase !== 'cycling') return fail('stale-or-inactive-cycle');
      check(Number.isFinite(seconds) && seconds >= 0 && seconds <= .25, 'Use bounded active-time steps of at most 0.25 seconds');
      return exclusive(() => {
        if (phase !== 'cycling' || runToken !== token) return fail('cycle-invalidated');
        elapsed = Math.min(cycleSeconds, elapsed + seconds);
        if (cycleSeconds - elapsed < 1e-9) { elapsed = cycleSeconds; pressure = target; phase = 'idle'; target = null; token = null; }
        return {ok: true, complete: phase === 'idle'};
      });
    },
    pause() { return exclusive(() => { if (phase !== 'cycling') return fail('No running cycle'); phase = 'paused'; token = null; return {ok: true}; }); },
    resume() { return exclusive(() => {
      if (phase !== 'paused' || !bothSealed()) return fail('No intact paused cycle');
      phase = 'cycling'; token = Object.freeze({}); return {ok: true, token};
    }); },
    cancel() { return exclusive(() => {
      if (!busy()) return fail('No active cycle');
      phase = 'idle'; pressure = 'unknown'; target = null; elapsed = 0; token = null; reason = 'Cycle cancelled; simulated pressure remains unknown'; return {ok: true};
    }); },
    dispose() {
      check(!locked, 'Reentrant airlock operation');
      if (!disposed) { invalidate('Disposed; create a fresh component after package replacement'); phase = 'disposed'; disposed = true; }
    },
  });
}
