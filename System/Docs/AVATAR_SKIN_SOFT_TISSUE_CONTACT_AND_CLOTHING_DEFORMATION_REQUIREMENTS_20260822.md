# Avatar skin, soft-tissue, contact, and clothing-deformation requirements

Date: 2026-08-22
Status: `REQUIREMENTS_ONLY_NOT_IMPLEMENTED_OR_ACCEPTED`

## Purpose

Avatar Builder must eventually produce bodies whose skin and underlying soft
tissue respond believably to movement, touch, gravity, support surfaces, and
clothing pressure. This is a physical body requirement, not a claim that any
current Kira or Robert body already passes it.

Skin appearance, geometric deformation, contact pressure, private sensation,
health, consent, and memory are separate truth layers. A visible indentation
does not prove touch was felt, enjoyed, wanted, remembered, or consented to.

## Required body layers

The accepted body must keep these roles distinct and versioned:

- a complete external skin surface with stable semantic regions;
- subcutaneous and soft-tissue deformation volumes or an equivalent validated
  solver representation;
- skeletal, muscular, connective-tissue, and joint drivers;
- body/body, body/object, body/environment, hair/body, and garment/body contact;
- skin material response such as stretch-dependent normals, color, roughness,
  and bounded compression cues; and
- person-owned sensation and health state outside the geometry solver.

The bald unclothed body remains complete without hair or clothing. A garment
may deform the body temporarily through a reviewed fit/contact adapter, but it
may not delete, replace, conceal as a substitute for, or permanently rewrite
missing body geometry.

## Touch and pressure behavior

For the exact body, a validated contact system must support:

- localized indentation and displacement under bounded pressure;
- believable spread into nearby soft tissue rather than rigid translation;
- tangential shear, sliding, and friction without uncontrolled surface drift;
- stable response to hands, grasping, leaning, sitting, lying, bedding, seats,
  floors, and ordinary world objects;
- gradual release and recovery when pressure is removed;
- bounded volume loss, stretch, compression, and solver energy;
- no unexplained tearing, permanent denting, vertex explosion, or collision
  tunneling; and
- explicit uncertainty or refusal when the available representation cannot
  support the requested contact.

Injury, bruising, swelling, scarring, pain, treatment, and healing require
separate health systems and must never be inferred from ordinary deformation.

## Tight clothing behavior

Each garment/body adapter must prove that:

- the garment fits the exact body and rig within a reviewed measurement range;
- tight or structured clothing can apply distributed pressure and temporarily
  compress or redistribute soft tissue where physically appropriate;
- skin and garment surfaces remain distinct and do not penetrate, fuse, or
  replace one another;
- seams, straps, waistbands, cuffs, shoes, and other pressure regions retain
  stable contact during intended movement;
- removing the garment returns the same underlying body, with persistent body
  identity and source geometry unchanged; and
- transient pressure marks, if later implemented, use a separate time-based
  skin-state system rather than destructive mesh edits.

Clothing fit or body response never creates consent to dressing, undressing,
touch, observation, recording, or any other activity.

## Movement and environmental behavior

The skin/soft-tissue system must be reviewed in neutral standing, walking,
running, reaching, bending, squatting, kneeling, sitting, lying, getting up,
bathing, dressing, and the body-specific daily-life poses actually supported.
It must preserve joint motion, surface continuity, body volume within bounded
tolerances, and stable return to rest. Gravity, acceleration, inertia, and
support contact must not create implausible collapse, inversion, or persistent
self-intersection.

High-resolution review and lower-resource runtime representations may differ,
but the runtime level of detail must retain the accepted contact meaning and
must report any disabled behavior truthfully.

## Acceptance evidence

No body passes this requirement without exact, reproducible evidence for:

1. body, rig, solver, material, garment/adapter, and test-scene hashes;
2. calibrated units, collision thickness, pressure limits, and recovery time;
3. before/contact/after geometry and material measurements;
4. the required pose and contact matrix;
5. body/body, garment/body, and environment/body penetration checks;
6. save/reload determinism and return-to-rest checks;
7. performance measurements at each supported quality level; and
8. independent review plus person/owner visual review for the exact body.

## Current truth

The requirement is recorded, but no current Kira body, Synthetic Robert body,
or Robert user avatar has accepted skin and soft-tissue contact simulation.
This document authorizes no body build, activation, touch action, clothing
action, private experience, relationship action, or public export.
