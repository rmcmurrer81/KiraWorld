import {NAVIGATION_CONTRACT, checkWalkSpawn, checkHorizontalRoute} from './horizontal_navigation.mjs';

export const AVATAR = Object.freeze({radius: 0.34, height: 1.68, eye: 1.56});
export function createWalkController(geometry) {
  const nav = {contract:NAVIGATION_CONTRACT, support_surfaces:geometry.support_surfaces, colliders:geometry.colliders};
  const room = geometry.rooms.find(r => r.id === geometry.connectivity.entry_room_id);
  if (!room || room.access !== 'walkable_layout') throw new Error('The entry room is unavailable for walking.');
  let feet = [room.x + room.width / 2, room.floor_y, room.z + room.depth / 2];
  const spawn = checkWalkSpawn(feet, nav, AVATAR.radius, AVATAR.height);
  if (!spawn.ok) throw new Error('No supported entry position: ' + spawn.reason);
  let yaw = 0, pitch = 0, blocked = null, distance = 0;
  const first = geometry.routes.find(r => r.points.some(p => p.every((v,i) => v === feet[i])));
  if (first) {
    const index = first.points.findIndex(p => p.every((v,i) => v === feet[i]));
    const next = first.points[index + 1] || first.points[index - 1];
    if (next) yaw = Math.atan2(next[0] - feet[0], -(next[2] - feet[2]));
  }
  function snapshot() {
    const current = geometry.rooms.find(r => r.access === 'walkable_layout' && r.floor_y === feet[1] &&
      feet[0] >= r.x && feet[0] <= r.x+r.width && feet[2] >= r.z && feet[2] <= r.z+r.depth);
    return Object.freeze({feet:Object.freeze([...feet]), yaw, pitch, blocked, distance,
      roomId:current?.id || null, roomName:current?.name || 'Passage'});
  }
  function look(dx,dy) {
    if (!Number.isFinite(dx) || !Number.isFinite(dy)) throw new TypeError('Invalid look input');
    yaw += Math.max(-500,Math.min(500,dx))*0.002;
    pitch = Math.max(-1.2, Math.min(1.2,pitch-Math.max(-500,Math.min(500,dy))*0.002));
    return snapshot();
  }
  function step(seconds,input={}) {
    if (!Number.isFinite(seconds) || seconds < 0) throw new TypeError('Invalid elapsed time');
    const dt=Math.min(seconds,0.05);
    yaw += ((input.turnRight ? 1:0)-(input.turnLeft ? 1:0))*1.65*dt;
    const forward=(input.forward ? 1:0)-(input.backward ? 1:0);
    const side=(input.right ? 1:0)-(input.left ? 1:0);
    if (!forward && !side) return snapshot();
    blocked=null;
    const scale=2.2*dt/Math.max(1,Math.hypot(forward,side));
    const end=[feet[0]+(Math.sin(yaw)*forward+Math.cos(yaw)*side)*scale,feet[1],
      feet[2]+(-Math.cos(yaw)*forward+Math.sin(yaw)*side)*scale];
    const result=checkHorizontalRoute({id:'interactive_walk',avatar_radius:AVATAR.radius,avatar_height:AVATAR.height,points:[feet,end]},nav);
    if (result.status === 'clear') {distance+=Math.hypot(end[0]-feet[0],end[2]-feet[2]);feet=end;}
    else blocked=result.reason;
    return snapshot();
  }
  // No direct-position setter, fly mode, level snapping, or teleport route.
  return Object.freeze({snapshot,step,look});
}
