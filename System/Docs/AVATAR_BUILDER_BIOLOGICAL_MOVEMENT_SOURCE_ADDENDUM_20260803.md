# Avatar Builder biological-movement source addendum — 2026-08-03

Status: source-backed design guidance only. This document does not approve a
motion, body, rig, candidate, render, or runtime action. The exact owner
requirements and acceptance gates remain in
`AVATAR_BUILDER_BIOLOGICAL_MOVEMENT_REQUIREMENTS_20260803.md`.

## Locomotion arm motion

Primary biomechanics evidence does not support a rigid arms-out pose or one
fixed shoulder-angle recipe for walking, jogging, and running.

- Collins, Adamczyk and Kuo found that ordinary walking arm swing is largely a
  low-torque, naturally coupled response to lower-body and trunk motion. Normal
  reciprocal swing reduced vertical ground-reaction moments and metabolic cost
  compared with constrained or opposite-phase swing. Source:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC2817299/
- Pontzer and colleagues reported that the arms act as mass dampers during
  walking and running, coupled through pelvis, trunk, and shoulder motion.
  Source: https://pubmed.ncbi.nlm.nih.gov/19181900/
- A motion-tracking study of adults reported mean dominant-elbow walking range
  of motion of 29.7 ± 10.2 degrees in flexion/extension and 14.2 ± 3.2 degrees
  in pronation/supination. These are observed cohort values, not universal
  limits or an identity-specific prescription. Source:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10277704/
- Full-body running simulations distinguish running from walking by active arm
  control and larger elbow flexion; active running arm swing reduced torso
  rotation and total modeled metabolic cost relative to passive or fixed arms.
  Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC11929735/

Avatar Builder consequences:

1. Neutral starts and finishes with relaxed arms near the torso, not a T- or
   A-pose presentation.
2. Walking uses smooth contralateral arm/leg phase coupled to pelvis and trunk,
   with low apparent shoulder effort and no shoulder locking.
3. Jog and run are separate clips. Speed may increase swing amplitude and
   elbow flexion, but no single research mean is copied as a hard constant.
4. Every candidate must expose shoulder, elbow, forearm, wrist, and hand
   trajectories, left/right phase, pelvis/trunk counter-rotation, foot contacts,
   center-of-mass/support state, and self-collision results.
5. Person-specific proportions, comfort, asymmetry, carried objects, fatigue,
   injury, and chosen style may alter motion. Such variation must be recorded,
   not silently forced into a generic gait.

## Handwashing sequence

The CDC's current community handwashing sequence is: wet under clean running
water, apply soap, lather all hand surfaces including backs/between fingers/
under nails, scrub for at least 20 seconds, rinse under clean running water,
and dry with a clean towel or air dryer. Source:
https://www.cdc.gov/handwashing/

Avatar Builder must therefore render and validate a time-based sequence rather
than a single hands-near-sink pose. The existing owner-required phases—sink
approach, water control, wetting, soap, palm/back/interdigital/thumb/fingertip/
wrist coverage, rinse, shutoff, dry, release, and neutral recovery—are a
motion-evidence expansion of that sequence. A rendered pose does not by itself
prove water flow, soap transfer, duration, cleaning, or drying; corresponding
runtime fixture and elapsed-time state must exist before those experience
claims are allowed.

## Object, door, shower, and bath truth boundary

For a book, tablet, phone, door, faucet, shower control, grab bar, towel, or
bath support, an animation name or parent constraint is not contact evidence.
Acceptance requires approach, preshape, measured finger/thumb contact, stable
support or grip, object/fixture response, release, withdrawal, balance, and
collision-free whole-body evidence at sampled phases.

Shower and bath actions remain distinct. A shower action does not approve tub
entry, lowering, seated support, rising, or tub exit. Neither action proves
cleaning, comfort, water temperature, or a completed experience without exact
runtime state and time progression.

## Transfer rule

These sources constrain the reusable method, not Kira's identity or exact
motion. Avatar Builder may reuse phase structure, instrumentation, and
biomechanical gates. It must retarget joint trajectories to each accepted
body/rig and rerun contact, balance, deformation, and owner-review evidence.
No pending movement is promoted by this addendum.
