# Avatar Builder biological movement requirements — 2026-08-03

Status: requirements and validation preparation only. Every motion described
here is **pending, unrendered, and unapproved**. This record does not validate
an existing body, pelvis, rig, action, clip, prop interaction, or runtime.

The machine-readable controlling addendum is:

`Avatar/movement_library/avatar_builder_biological_movement_requirements_20260803.json`

## Owner decisions recorded

- A neutral standing body must settle into a natural relaxed stance. The arms
  must not remain abducted in a T-pose or A-pose presentation.
- Walk, jog, and run each require pace-specific, contralateral biological arm
  swing. Passing one pace does not approve the other two.
- Book, tablet, and phone handling each require articulated reach, hand
  preshape, finger/thumb contact, stable grasp/hold, return, release, and
  withdrawal evidence for the exact prop.
- Door use requires the real hand to reach and grip the exact handle, operate
  the lever or knob, maintain contact while unlatching, then coordinate either
  push or pull with body balance, stepping, door-sweep clearance, and release.
- Handwashing requires a complete staged sequence covering sink approach,
  water control, wetting, soap, palms, backs of hands, between fingers, thumbs,
  fingertips, wrists, rinse, shutoff, drying, release, and neutral recovery.
- Shower and bath validation each require entry, support and balance, control
  operation, articulated washing, exit, towel interaction, and recovery. A
  shower pass cannot stand in for a bathtub pass or vice versa.
- No pelvic candidate is owner-approved. Movement evidence cannot silently
  select or approve a pelvic candidate and cannot substitute for anatomy
  review.

## Required owner-review views

Every future complete body review must include:

- full-body front;
- left and right obliques;
- left and right side views;
- rear;
- a protected private underside/perineal clinical view;
- seated support/contact;
- bend/deformation evidence.

Motion packages additionally need phase-bound full-body views and close contact
views. Each rendered image must identify the candidate, rig, motion/action,
phase/frame, camera, exact prop or fixture, and its own SHA-256.

## What counts as movement evidence

A clip name, keyframes, a successful script return, parenting a prop to a hand,
opening a door after a timer, or rendering one attractive frame is not a pass.
A motion remains `PENDING_UNAPPROVED` until all of the following exist for the
exact candidate and action:

1. neutral start and neutral return;
2. phase-by-phase rendered evidence;
3. measured intended contacts;
4. whole-body self-intersection checks at every sampled phase;
5. body/prop/environment penetration checks at every sampled phase;
6. support, balance, root-travel, and foot-plant traces that agree with the
   visible motion;
7. no hidden proxy limb, teleported prop, parenting-only grip, or timing-only
   success;
8. Robert's explicit approval of that exact rendered motion candidate.

Walk, jog, and run must prove contralateral arm/leg timing, shoulder/elbow/wrist
trajectories, foot contact, balance, and collision-free arm clearance. Object
handling must prove exact-object contact continuity through grasp and release.
Door push and pull are separate tests because their stance, stepping, balance,
and door-sweep hazards differ.

Handwashing, showering, and bathing also retain an activity-truth boundary: a
posed animation does not prove that water flowed, soap transferred, the body
was cleaned or dried, or the resident experienced or completed the activity.
Those claims require separately connected runtime state and time-based
experience evidence.

## Append-only preservation

This addendum does not edit or replace the existing foundation movement
manifest, Attempt-04 movement preparation, any Blend, GLB, render, candidate,
or prior evidence. Existing motions retain their recorded status. These new
requirements add stricter future gates; they do not retroactively turn a draft
motion into a failure or an approval.

No Blender, rendering, GPU, runtime activation, movement authoring, body
selection, export, or publication was authorized or performed by this record.

