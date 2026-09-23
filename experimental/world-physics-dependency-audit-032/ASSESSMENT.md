# Physics dependency audit032

Do not install019 as an optimization for the current015 physics. Its only
performance change replaces key construction inside `finite_top_domain.mjs`.
The installed runtime has neither that file nor any `finiteTopDomain` references.
There is no performance-only patch from019 that can be applied to015. Adding the
unused helper would do nothing; importing it and wiring its calls would introduce
the unapproved017 behavior. No replacement optimization was invented for this audit.

The historical18.5–19.6% reduction was relative to017, not015. Fresh short timings
reinforce the distinction:12 frames took0.622 seconds in the actual installed015,
0.627 in its frozen copy,2.555 in017 and2.065 in019.019 was still about3.32 times the
installed stepping time. Execution order rotated each frame, but this small run is
not a statistical benchmark or a guaranteed performance result.

## Exact source relation

All four canonical physics files match the preserved019 `baseline` bytes. The
four existing019 physics modules match017; the helper's `key` function is their
sole019 delta. The normalized patches remove line-ending noise only; exact source
bytes and SHA256 pins remain in `sources/` and `PLAN.json`.

| File | Changes required to get from015 to019 |
| --- | --- |
| bedding_base.mjs | Cloth.predict observes each position prediction. Cloth.solve observes each endpoint correction and the grab write. |
| frame_contacts.mjs | project observes each corrected vertex after its three coordinate updates. |
| mattress_physics.mjs | Adds the helper import and changes the contact-direction limitation. MattressSurface.predict and solve observe top geometry mutations. collideCloth observes head/floor/top corrections and skips the upper barrier for certified particle paths. BeddingSimulation.constructor attaches a domain; step checks observed positions at each substep's boundaries; metrics exposes the domain snapshot. |
| surface_contacts.mjs | edgeContact and interiorContact can suppress contacts and report hits using domain certificates. project observes corrected positions. finishSurfaceContactVelocities can skip an impulse for a certified path. |
| finite_top_domain.mjs | Entirely new015 dependency: FiniteTopDomain constructor, hold, mask, observeVertex, observeTop, bindings, verifyOwnedPositions, clear, snapshot; attachFiniteTopDomain; key.019 changes only key relative to017. |

The existing015 string keys have different purposes and semantics. Surface
topology creates edge keys once; compileFrame creates rounded plane keys once.
Velocity contact maps use ordered `ids.join(',')`, with frame-part identity where
applicable.019 sorts IDs and prefixes their count. Substituting its helper into
these maps would change key semantics rather than transplant an equivalent patch.
No profile or measured installed015 bottleneck warrants that separate alteration.

## Deterministic checks actually completed

`check_relation.mjs` verified16 original and snapshot source/fixture/evidence
SHA256 bindings before and after one bounded CPU process. The node process used
a384 MiB heap cap and exited normally in6.30 seconds under a30-second deadline.
No model, GPU, browser, owner world or canonical-file write occurred.

- Twelve default wide-bed frames ran through the actual installed import, frozen015,
  frozen017 and frozen019:725 cloth nodes,651 mattress nodes,40 iterations and
  four substeps each. Every frame matched all three bodies' p/prev/v bytes.
- Installed015 matched its frozen copy's complete metrics. The compact015/017
  trajectory rows, including Node702 position/previous/velocity, matched the
  saved017 `FULL-PILOT-RESULT.json` baseline and candidate observations exactly.
-017 and019 also matched complete metrics, domain masks, previous observed
  positions, primitive certificates and counters at every checked frame.
- A separate inherited9-node frame-clear underside fixture began with all body
  states equal. After one frame, installed015 reached a maximum cloth height of
  0.7873741923382076m;017 and019 remained at or below0.2m.017/019 stayed byte-identical
  through ten pin/release frames, with zero reported frame intersections or
  surface contacts. This is an explicit behavioral distinction, not a quality pass.

The output retains per-frame state hashes and compact trajectory rows. This is
not a full1110-frame saved-state replay. The scoped initial-state match cannot
override the demonstrated later/alternate-state behavior difference.

## Installation decision and next useful work

Leave current physics015 installed and017/019 isolated. The existing public019
backup remains a valid optimization of that experimental domain implementation.
No canonical installation plan is supplied because there are zero applicable
019 performance-only changes in015.

Promotion of017/019 would require a separate contact-behavior review: independent
finite-volume contact checks, a credible ownership boundary for mutable positions
and certificates, and an explicit treatment of the missing side/underside response.
Its own gated reporter cannot independently prove those properties. Longer timing
runs or further key micro-optimizations would not address them. Visual appearance,
material realism and owner acceptance remain separate and unestablished by032.
