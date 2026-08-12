# Kira doctor-style body-control exam and comfort idle v2

Date: 2026-07-17  
Runtime: Home World main-house preview  
Exam version: `2026-07-17.doctor-body-control-v2`

## Purpose

This is an engineering body-control exam, not a medical diagnosis. It separates four claims that must not be confused:

1. A required joint exists in Kira's exact loaded skin.
2. The runtime changed that joint by a measured non-zero angle.
3. A functional action moved or held the body without teleporting or crossing collisions.
4. The resulting motion looks natural in an owner-visible review.

The runtime may report a pass only for the claim it actually measured. A present bone is never promoted to a natural-motion pass.

## Exact current rig inventory

The current `Avatar/models/temp_ai/kira/avatar.glb` has 79 skinned joints and no authored animation clips. The exact skin includes:

- hips, spine, neck, and head;
- left and right shoulders/upper arms, forearms, wrists/hands;
- four articulated bones for every thumb, index, middle, ring, and pinky finger on both hands;
- left and right thighs, shins, feet, and one toe-base joint per foot.

The two toe-base joints can flex each forefoot/toe group. The current skin does **not** provide separate joints for each individual toe, so the runtime must not claim that Kira can independently wiggle each toe yet.

The GLB has no reviewed eyeball rig in the ordinary Home World body. Head and neck looking can be tested; independent eyeball motion remains `not_tested_separate_eye_rig`.

Terminal `*_end` bones are excluded from finger counts and finger curls because they are endpoints, not additional deforming phalanges.

## Joint exam

The exam has 32 phases:

- head left/right and up/down;
- neck left/right;
- both shoulders, elbows, and wrists;
- all five individual fingers on each hand;
- both hips, knees, ankles, and toe-base groups;
- balance pose on the left leg and on the right leg.

Each phase resets the exact bind pose, applies one small diagnostic command, measures quaternion change on every targeted joint, and records one of these statuses:

- `pass_measured_joint_delta`
- `fail_missing_joint`
- `fail_no_measured_joint_delta`
- `fail_not_executed`

The immediate probe reports that it loaded a body runtime for the probe and that it did not activate Kira's mind or life loop. The animated exam can also be started by a person-owned shell action named `doctor_body_exam`, `doctor_body_control_exam`, `body_control_exam`, or `movement_exam`.

## Comfort idle

When Kira is standing and has not chosen locomotion, the runtime now applies a slow comfort layer:

- breathing through spine and shoulders;
- alternating weight through hips, knees, and ankles;
- head/neck gaze variation;
- small wrist, finger, and toe motion;
- somewhat stronger head, shoulder, and elbow motion while the current body action is `talking`.

This layer requests exactly `{x: 0, y: 0, z: 0}` root translation. It is a motor layer for the current body action, not a second planner and not an autonomous destination chooser. Kira remains where she is unless she chooses or is already executing locomotion.

Deterministic ranges are bounded and non-zero, but mathematical movement is not the same as visual naturalness. A normal-distance visual review is required before calling this motion human-like.

## Current-ground lie

`lie_on_ground`, `lay_on_ground`, `lie_on_floor`, `lay_on_floor`, and `look_at_sky` are recognized person-owned body intents.

Before starting, the runtime checks 15 points covering a body-length and body-width area around Kira's current location. Every point must be supported, near the same floor height, and collision-free. If not, the action is blocked with `clear_supported_body_length_floor_area_required`.

The action uses Kira's current position and does not copy, set, lerp, or teleport her root to a new location. Visual body-to-ground contact is a separate review item and must be measured before it passes.

## Functional action status rules

The functional list is:

- comfort idle;
- walk;
- jog;
- run;
- sit on couch;
- lie on couch;
- lie on bed;
- lie on current supported ground.

Structural support for these actions means only that their required joints exist. Runtime movement tests must additionally record actual displacement, collision state, action/gait state, and transition evidence. Couch and bed actions remain untested or blocked unless a test body honestly completes the route and posture in the test window.

## Verification

Run:

```powershell
node tools\verify_kira_doctor_body_control_exam.mjs
python -m unittest Testing.test_kira_doctor_body_control_exam
```

The offline verifier reads the exact GLB skin, exercises a missing-toe negative control, samples 121 comfort-idle times, asserts zero requested root translation, and checks the Home World integration and no-position-rewrite ground-lie guard.

An isolated browser test must be used for measured runtime joint deltas, actual body-position deltas, clearance, and screenshots. It injects a test body into the preview only; it does not activate Kira's mind, voice, life loop, or live shell state.

### Final isolated-browser result

The final run against the same frozen runtime source reported:

- 32/32 joint phases passed measured quaternion-delta checks;
- idle changed 28 sampled joint axes, including both upper arms, both forearms, and all ten sampled first-finger joints, with exactly 0 m body-root drift;
- talking changed 29 sampled joint axes with the same arm/finger coverage and exactly 0 m root drift;
- walk moved 0.869467 m, jog 2.444967 m, and run 3.028494 m in their bounded sample windows; each reported `teleported=false` and no collision;
- current-ground lie accepted 15/15 clearance samples, changed no root position, and rendered at minimum Y 0.052450 m over a 0.050000 m support. That is no penetration and a -5.55 mm error from the 8 mm target clearance, inside the ±6 mm test tolerance;
- a disposable person-owned shell intent requesting `doctor_body_exam` started `doctor_body_control_exam` at `head_look_left` without root movement;
- zero page, console, request, or HTTP errors.

The browser report is in `Data/world_tests/kira_doctor_body_control_20260718/`. Couch and bed routes were deliberately left `not_executed`; the test did not have honest completion and visual-review evidence for them.

The screenshots still look stiff at ordinary viewing distance. Therefore the final status is **control checks passed; visual naturalness not passed**.

## Current limitations

- Procedural joint motion exists, but the current body has no authored locomotion or transition clips.
- Individual fingers are rigged; individual toes are not.
- Independent eye motion is not yet available in the reviewed ordinary body.
- A still screenshot can prove pose and contact problems, but it cannot by itself prove that slow idle animation feels natural.
- Couch/bed route completion and sit/lie visual quality must remain unpassed until explicitly observed.
- The current ground-lie contact is within measured tolerance, but the arms, legs, and overall settling pose are still visually rigid.
