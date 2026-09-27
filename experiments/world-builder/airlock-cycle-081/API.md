# API contract

The module is dependency-free ECMAScript. It exports `CONTRACT`, `LABEL`, `bindAirlockCycle` and `createAirlockCycle`.

## Association

`bindAirlockCycle(metadata, options)` returns an immutable association. Supply already authenticated `world_scene_metadata_v2` metadata and these options:

- `manifestSha256` and `sceneSha256`: exact admitted manifest and scene-metadata byte hashes. Actual GLB validation is a separate mandatory host step.
- `pairId`, `insideDoorId`, `outsideDoorId`: exact unique metadata identities.
- `roleAssignment`: exactly `explicit_fictional_habitat_mars`, with that fictional mapping disclosed in the host UI.

The binder checks paired interlock policies, room adjacency, leaf and portal association, session-local behavior, initially closed doors and supported signed quarter-turn hinges. It checks association, not file authenticity. A copied or reconstructed binding is not accepted by the constructor.

## Runtime ports

`createAirlockCycle({binding, runtimeIdentity, readDoors, toggleDoor, cycleSeconds = 6})` captures one specific runtime instance. Both callbacks must be synchronous and must retain that same runtime reference. The authored duration must be finite and between 2 and 30 seconds.

`readDoors()` returns `{runtimeIdentity, manifestSha256, sceneSha256, sceneId, doors}`. The two nominated observations each contain `{id, angle, target, moving, motionHeld}`. Angles and targets must match the nominated hinge convention. The wrapper refreshes these observations before state changes and active progress. Missing/invalid poses or changed identity fault the cycle.

`toggleDoor(doorId)` invokes the host's normal guarded toggle operation and returns `{ok: boolean, reason?}`. It must synchronously expose the new target/motion outcome to `readDoors`; physical animation may continue under the host. The normal runtime retains reach, occupancy, swing, collision and interlock rules. A refusal or unobserved outcome must not be reported as success.

## State methods

`snapshot()` refreshes observations and returns an immutable state with the fictional label/capability limits. **On a read failure, its `doors` field may still be the last valid observation. The host must label that display unavailable or last observed; it has no explicit observation-valid flag.** Conservatively display door poses as unavailable whenever the component is faulted, unless an independent successful authoritative observation is shown separately.

`acknowledgeSimulatedSeal(side, value = true)` accepts `inside` or `outside`, only when geometrically closed/stopped and no cycle is active. This acknowledgement is not a real seal sensor or mechanical latch.

`begin(destination)` accepts `habitat` or `mars`, requires both acknowledgements and geometric closure, and returns `{ok: true, token}`. Completion sets only a symbolic pressure state. The token is an opaque object, local to this exact instance and active run.

`advance(token, seconds)` accepts finite active-time slices from 0 through 0.25 seconds. The host must supply truthful bounded elapsed active time. It does not schedule itself. Stale, foreign or inactive tokens return a refusal without advancing state.

`pause()` retains elapsed progress and revokes the token. `resume()` requires an intact paused cycle and returns a fresh token. `cancel()` clears progress and leaves symbolic pressure unknown. A new full cycle is necessary after cancellation.

`open(side)` requires compatible symbolic pressure plus the peer's geometric closure and acknowledgement, then delegates the normal runtime command. `close(side)` delegates closing without restoring pressure or acknowledgements. Moving/held doors are refused. Commands during an active or paused cycle are refused until cancellation.

`dispose()` invalidates the instance permanently and does not move a door. Late tokens cannot read or command the old runtime. No method saves state to disk.
