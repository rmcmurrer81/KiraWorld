# Fictional latch/contact visual component084

Original experimental Three.js artwork: three telescoping bolts enter hollow keepers, two control wheels turn, and a gasket approaches a closed-leaf contact plane. This is an isolated reusable component. It is **not integrated or installed**, and it has no door-permission, collision, pressure or package-admission authority.

The geometry illustrates an authored fictional mechanism. The gasket motion, bolt insertion depth and 0.8-second pacing are artistic parameters, not a material calculation, leak test, physical airlock, engineering certification or VR capability. A successful visual endpoint never acknowledges a simulated seal or permits a door to open.

`describeLatchVisual(plan)` returns a frozen visual recipe and proposed bolt endpoint bounds from the expected authored-hatch recipe shape. `createLatchVisual({THREE,plan,doorId,runtimeIdentity,readDoor,isCurrent})` returns its owned `root`, `recipe`, `snapshot()`, and these host-driven methods:

- `request(boolean)` selects engagement/release. Engagement requires the exact current door to be closed, stopped and targeted closed.
- `advance(seconds)` accepts finite steps from 0 through 0.05 seconds. No timers, animation loops or background jobs are created.
- `syncDoor()` validates the exact runtime/door observation and follows a released door's angle. Identity loss, bad observations or door motion during engagement hide and reset the artwork with a fault.
- `pause(reason)` and `resume(reason)` aggregate independent holds. Removing one hold cannot override another; only explicit subsequent time steps move the artwork.
- `reset()` invalidates an in-flight observation, retains pause reasons and rechecks the current identity.
- `dispose()` is idempotent, detaches the component and disposes only its owned geometries/materials. Later operations cannot read the runtime or revive it.

`readDoor` returns `{runtimeIdentity,id,angle,target,moving}`; `isCurrent` must come from the host's actual loaded-object identity. The component begins hidden until its first valid observation. `snapshot()` reports the last observation and visual state, not live telemetry. Reentrant reset/disposal is guarded.

The existing static hatch package declares different hardware and collider bounds. **Do not overlay this artwork on an old imported package and treat its old metadata as valid.** Integration requires a reviewed shared-authoring, collision, export and strict-import successor. See `INTEGRATION.md`.

The included tests use invented plans and synchronous runtime doubles. They verify CPU geometry/state/lifecycle behavior only. There is no private scene package, rendered preview, audio, media, model, browser approval, headset approval or physical-pressure proof in this backup.
