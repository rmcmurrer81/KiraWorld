# World024 working doors — isolated candidate

This adds visible framed hinged leaves, inset panels and handles, nearby F/button
interaction, timed opening/closing and collision driven by the same door pose.
The walker stops at a closed leaf and can cross after it opens. Movement keeps
the existing supported-floor and static-wall checks. Closing is refused across
an occupied swing, and ongoing motion pauses if the walker enters that area.

Door state is local to one preview session. This does not implement pressure
seals, airlock interlocks, emergency egress, calibrated rigid-body dynamics or
saved door state. Rotated leaves use conservative axis-aligned collision bounds;
the full quarter-disc sweep is conservatively blocked rather than pushing or
teleporting the walker.

Only four proposed installed assets changed: `walk_controller.mjs`, `viewer.mjs`,
`index.html` and `style.css`. Door logic is exported from the existing walker
asset, so the preview allowlist need not expand. No canonical file was changed.

## Validation and review

`TEST-RESULT-003.json` records33 checks over four synthetic x/z orientations and
both swing sides. The tests use the actual walker callbacks, collision routines,
source immutability, independent states, reach/elevation checks, bad inputs,
closing occupancy and furnished geometry guards. Earlier receipts are historical
snapshots before the optional furnishing interface was added.

`EXISTING-LAYOUT-DOOR-CHECK.json` independently checks all six portals in the
existing Mars geometry: closed blocking and open forward/reverse traversal, plus
entry spawn. Source geometry and its manifest remained unchanged. This is
technical proof only. Robert rejected the existing Mars room appearance; no
room realism or overall world approval is claimed.

An immutable copy of that existing layout is staged under candidate/Data for
door-only visual review. `PREVIEW-PLAN.json` pins the exact candidate assets,
unchanged backend and121 protected source/owner files. Neither a server nor a
browser was launched by this agent. Root must coordinate graphics before using
`serve_preview.py --expected-plan-sha256` with the recorded plan hash. The server
is loopback-only, serves the existing exact asset allowlist, caps itself at300
seconds and refuses a duplicate consumed review. Do not overwrite its receipts.

## Furnishing integration

Use `createWalkController(geometry, {extraColliders: plan.colliders})`.
The optional list accepts at most128 finite AABBs with unique IDs. It is copied
so later caller mutations cannot alter the active collision scene. Entry
overlap and obstruction of a door swing are rejected. Movement hitting furniture
reports `furniture_obstruction`.

`createDoorSystem(geometry).assemblies()` exposes immutable `swingBounds` for
each door; keep furnishings outside those volumes. Rendering and furniture
collision should come from the same plan. This024 viewer still supplies no
furnishings; root owns the separate025 dressing work.

## Installation hold

Do not install these assets yet. Existing immutable previews pin both copied
assets and their original engine-source paths. Replacing the current renderer
would therefore invalidate old saved previews under the current verifier.
The separate026 compatibility candidate must be reviewed and integrated first.
Existing saved projects, original media, World015 physics and the installed023
saved-reopen feature remain untouched by024.
