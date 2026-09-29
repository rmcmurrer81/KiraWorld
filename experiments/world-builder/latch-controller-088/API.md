# Candidate API — source only

Producer `createDoorSystem(geometry, {hatchGeometry: true, hatchVariant: 'latched_v2', isCurrent})` keeps all prior door methods and adds:

- `requestLatch(id, boolean, feet)`: engage/release that exact hatch, with reach and current-session checks.
- `releaseAndOpen(id, feet)`: queue one release-then-open intent. Does not instantly move an engaged leaf.
- `latchStates()`: immutable snapshots, including fraction, target, pause reasons, fault and last opening result.
- `pauseLatches(reason)`, `resumeLatches(reason)`: named pause ownership; pause cancels pending opening.
- `dispose()`: terminal retirement.

`advance(seconds, feet, ...)` remains the only time owner. It advances latch state once, commits any newly ready intent once through the real guarded toggle, then advances admissible hinges. The v1 default remains `legacy_v1`. It is invalid to request v2 with `hatchGeometry: false`.

Producer `createWalkController(geometry, {extraColliders, hatchVariant, isCurrent})` forwards the same methods with the actual current feet, so its `requestLatch(id, boolean)` and `releaseAndOpen(id)` take no position override. `step()` owns the time advance.

Portable `createDoorRuntime(metadata, {isCurrent})` adds the equivalent methods with portable IDs (`door:<portal>`). Portable `createRuntime(metadata, {isCurrent})` forwards them using actual feet and retains `step()` as clock owner. The provided predicate must be synchronous and return literal true only for the captured current session. Stale observation permanently retires the controller.

Metadata helper:

- `describeLatchedDoor(geometry, portalId) → {door, nodes, colliders}`.
- `validateLatchedDoor(door, nodeMap, colliderMap, wholeMetadata)` recomputes exact bounded recipe metadata and returns the admitted moving colliders.

This helper grants no package/file admission. Consumer083's existing unchanged loader still admits only its two exact legacy packages. A new loader/GLB binding and actual export remain future reviewed work.

For a later mesh adapter, consume `latchStates()` from the controller; do not instantiate or advance a second authority inside the renderer. The unchanged084/086 visual implementation is a geometry/pose reference, not a second active clock. Latch/door actions do not alter the separate fictional seal acknowledgement or pressure state.
