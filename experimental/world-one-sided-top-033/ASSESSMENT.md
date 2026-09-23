# One-sided top-contact experiment033: hold for further review

This is an isolated two-file experiment against installed015. It suppresses the
upper mattress barrier only when every vertex of the queried particle, edge or
triangle has finite current and physical previous positions strictly below the
fixed mattress bottom, including the original configured skin. It does not change
the solver coefficients, physical previous positions, head/floor/frame contacts,
iteration count, contact arithmetic or visible geometry.017 observers and hashed
primitive certificates are absent.

## What the default-frame divergence means

The first25 default wide-bed frames match015 byte for byte for cloth, mattress and
pillow p/prev/v. Frame26 differs. The exact-comparison harness stopped immediately
and retains its `HOLD_DEFAULT_TRAJECTORY_CHANGED` receipt; it did not complete60
frames or the reversed-order pilot.

The divergence includes a demonstrably spurious015 correction. A disposable
diagnostic copy recorded node714 at `(0.178785, 0.155181, 1.049581)` with physical
previous position `(0.178728, 0.146383, 1.060286)`. The mattress bottom was0.385m,
skin0.006m, width1.6m and length2.1m. The entire straight previous-to-current
segment lies more than22.38cm below the skin-expanded bottom. Current XZ is inside
the finite mattress footprint. Nevertheless015 moved that particle upward to
0.571145m, crossing the slab.033 correctly declines this particular top response.
Earlier node708 was just outside the raw footprint but inside its skin; its false
lift is also recorded separately and is not mislabeled as crossing the raw solid.

This classification uses independent rectangle clipping and a shared bottom
separating plane. It does not rely on033's surface reporter. At each saved event,
all actual top heights were checked finite and above the bottom. The instrumented
copies reproduce the saved uninstrumented state hashes exactly through frame26;
two added callbacks changed neither response nor arithmetic.

At frame26 the candidate reports1.877% maximum stretch and0.479m/s RMS speed;
015 reports5.438% and3.731m/s. Both report zero frame/surface intersections. These
measurements support removal of that artificial lift, but cannot prove every
other contact in the step is legitimate or that the resulting cloth looks real.
All725 cloth vertices differ after the coupled corrections propagate; the largest
positional difference is0.397m at node713.

## Tests, timing and unresolved limitations

- The original focused suite passed12 of13 assertions. The failed mixed-triangle
  test incorrectly expected the whole solve to remain byte-identical despite one
  separate edge being entirely below bottom. A targeted, unchanged-code check
  confirms the mixed triangle and its two mixed edges remain eligible, while the
  below-bottom edge is excluded; six constraints run instead of eight. Both the
  original failure and its clarification are preserved.
- Top-to-bottom crossing, long edges spanning the finite footprint, triangle
  interiors spanning it, finite-footprint rejection, boundary uncertainty,
  nonfinite/missing histories, stale below-bottom velocity impulses, six coupled
  supported-drop frames, ten underside pin/release frames and ten lateral-entry
  frames were exercised. The baseline underside fixture reaches0.787m;033 stays
  at or below its initial0.2m with no reported frame intersection.
- In one candidate-first26-frame run,033 stepping took1.578 seconds versus1.544
  for015, about2.2% more. The largest observed frame was78.84ms versus87.81ms.
  These are short timing observations, not a statistical benchmark, mathematical
  worst-case bound or general performance promise.
- A deliberate upward-then-return position excursion is invisible to this rule:
  endpoint separation is **not** a certificate for intermediate constraint paths.
  An underside particle rising into the slab still receives015's upper-barrier
  fallback; no underside or side collision response was implemented. Fixed-bottom
  and valid owned mattress geometry remain assumptions of this narrow experiment.

Status: **experimental, not installed, not a complete contact fix.** The default
divergence alone is not a reason to preserve015's bug; the independent geometry
supports the observed correction. Intermediate-history and unsupported-response
concerns still prevent claiming a certified finite-solid solver. Root review is
pending. No long replay or further physics variant followed the diagnosis.

A possible later approach is a per-substep conservative below-bottom flag updated
at every owned cloth position mutation, without017's per-primitive keys. That is
only a proposal: all write paths, finite top bounds, changes of support and mixed
primitive behavior would need review. It was not implemented in033. Metadata
ownership correction034 is the next priority.
